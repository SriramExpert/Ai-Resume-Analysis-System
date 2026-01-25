import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, create_engine, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

Base = declarative_base()

class SearchHistory(Base):
    __tablename__ = 'search_history'
    id = Column(Integer, primary_key=True)
    query = Column(Text, nullable=False)
    tool_detected = Column(String(50))
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ResumeMetadata(Base):
    __tablename__ = 'resume_metadata'
    id = Column(Integer, primary_key=True)
    candidate_name = Column(String(255), unique=True)
    source_file = Column(String(512))
    parsed_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatSession(Base):
    """Track conversation sessions for context-aware chat"""
    __tablename__ = 'chat_sessions'
    session_id = Column(String(36), primary_key=True)  # UUID
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    session_metadata = Column("metadata", JSON)  # Store session-specific data

class ChatMessage(Base):
    """Store individual chat messages with entity tracking"""
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('chat_sessions.session_id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    message = Column(Text, nullable=False)  # Original query/response
    resolved_query = Column(Text)  # Query after context resolution (for user messages)
    entities_mentioned = Column(JSON)  # Extracted entities with LLM-determined types
    timestamp = Column(DateTime, default=datetime.utcnow)


class PostgresHandler:
    """Handle PostgreSQL operations for metadata and logs"""
    
    def __init__(self):
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "resume_analysis")
        
        self.engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{db}')
        self.Session = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        try:
            Base.metadata.create_all(self.engine)
        except Exception as e:
            print(f"Warning: Could not connect/create tables in PostgreSQL: {e}")

    def save_metadata(self, name, source, data):
        session = self.Session()
        try:
            metadata = session.query(ResumeMetadata).filter_by(candidate_name=name).first()
            if metadata:
                metadata.source_file = source
                metadata.parsed_json = data
            else:
                metadata = ResumeMetadata(candidate_name=name, source_file=source, parsed_json=data)
                session.add(metadata)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error saving metadata: {e}")
        finally:
            session.close()

    def log_query(self, query, tool, response):
        session = self.Session()
        try:
            log = SearchHistory(query=query, tool_detected=tool, response=str(response))
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error logging query: {e}")
        finally:
            session.close()
            
    def get_all_resumes(self):
        session = self.Session()
        try:
            return session.query(ResumeMetadata).all()
        finally:
            session.close()

    # ===== Chat Session Management Methods =====
    
    def create_session(self, session_id: str, metadata: dict = None):
        """Create a new chat session"""
        session = self.Session()
        try:
            chat_session = ChatSession(
                session_id=session_id,
                session_metadata=metadata or {}
            )
            session.add(chat_session)
            session.commit()
            return chat_session
        except Exception as e:
            session.rollback()
            print(f"Error creating session: {e}")
            return None
        finally:
            session.close()
    
    def save_message(self, session_id: str, role: str, message: str, 
                     resolved_query: str = None, entities: list = None):
        """Save a chat message with optional entity tracking"""
        session = self.Session()
        try:
            # Update session last_activity
            chat_session = session.query(ChatSession).filter_by(session_id=session_id).first()
            if chat_session:
                chat_session.last_activity = datetime.utcnow()
            
            # Save message
            chat_message = ChatMessage(
                session_id=session_id,
                role=role,
                message=message,
                resolved_query=resolved_query,
                entities_mentioned=entities or []
            )
            session.add(chat_message)
            session.commit()
            return chat_message
        except Exception as e:
            session.rollback()
            print(f"Error saving message: {e}")
            return None
        finally:
            session.close()
    
    def get_session_history(self, session_id: str, limit: int = None):
        """Retrieve conversation history for a session"""
        session = self.Session()
        try:
            query = session.query(ChatMessage).filter_by(session_id=session_id)
            
            if limit:
                # Get last N messages: Order by DESC, Take N, then Reverse back to ASC
                query = query.order_by(ChatMessage.timestamp.desc()).limit(limit)
                results = query.all()
                return list(reversed(results))
            else:
                # Get all messages: Order by ASC
                query = query.order_by(ChatMessage.timestamp)
                return query.all()
        finally:
            session.close()
    
    def get_last_entities(self, session_id: str, n: int = 10):
        """Get entities from the last N messages in a session"""
        session = self.Session()
        try:
            messages = session.query(ChatMessage)\
                .filter_by(session_id=session_id)\
                .order_by(ChatMessage.timestamp.desc())\
                .limit(n)\
                .all()
            
            # Collect all entities from messages
            all_entities = []
            for msg in reversed(messages):  # Reverse to get chronological order
                if msg.entities_mentioned:
                    all_entities.extend(msg.entities_mentioned)
            
            return all_entities
        finally:
            session.close()
    
    def clear_session(self, session_id: str):
        """Clear all messages for a session"""
        session = self.Session()
        try:
            session.query(ChatMessage).filter_by(session_id=session_id).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error clearing session: {e}")
            return False
        finally:
            session.close()
    
    def session_exists(self, session_id: str):
        """Check if a session exists"""
        session = self.Session()
        try:
            return session.query(ChatSession).filter_by(session_id=session_id).first() is not None
        finally:
            session.close()

