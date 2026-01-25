"""
Chat History Manager - Orchestrates chat session management and context resolution
"""

import uuid
from typing import Optional, Dict, Any


class ChatHistoryManager:
    """
    Manages chat sessions, coordinates context resolution, and tracks entities.
    """
    
    def __init__(self, db_handler, context_resolver):
        """
        Initialize with database handler and context resolver.
        
        Args:
            db_handler: PostgresHandler instance
            context_resolver: ContextResolver instance
        """
        self.db = db_handler
        self.resolver = context_resolver
    
    def create_new_session(self, metadata: Dict[str, Any] = None) -> str:
        """
        Create a new chat session.
        """
        session_id = str(uuid.uuid4())
        
        # Add default metadata if none provided
        session_metadata = metadata or {
            "created_by": "System",
            "context_awareness": True,
            "version": "1.0"
        }
        
        self.db.create_session(session_id, session_metadata)
        return session_id
    
    def process_message(self, query: str, session_id: Optional[str] = None) -> dict:
        """
        Process user message with context resolution.
        
        Args:
            query: User's query
            session_id: Optional session ID (creates new if not provided)
            
        Returns:
            dict: {
                "session_id": str,
                "original_query": str,
                "resolved_query": str,
                "entities": List[dict],
                "context_applied": bool,
                "confidence": float
            }
        """
        # Create session if not provided
        if not session_id:
            session_id = self.create_new_session()
        elif not self.db.session_exists(session_id):
            # Session doesn't exist, create it
            self.db.create_session(session_id, {})
        
        # Resolve query using context
        resolution = self.resolver.resolve_query(query, session_id)
        
        # Save user message with entities
        self.db.save_message(
            session_id=session_id,
            role="user",
            message=query,
            resolved_query=resolution.get('resolved_query'),
            entities=resolution.get('entities', [])
        )
        
        return {
            "session_id": session_id,
            "original_query": resolution['original_query'],
            "resolved_query": resolution['resolved_query'],
            "entities": resolution.get('entities', []),
            "context_applied": resolution.get('context_used', False),
            "confidence": resolution.get('confidence', 1.0),
            "reasoning": resolution.get('reasoning', '')
        }
    
    def save_assistant_response(self, session_id: str, response: str, entities: list = None):
        """
        Save assistant's response to the session.
        
        Args:
            session_id: Chat session ID
            response: Assistant's response text
            entities: Optional list of entities mentioned in response
        """
        self.db.save_message(
            session_id=session_id,
            role="assistant",
            message=response,
            entities=entities or []
        )
    
    def get_session_history(self, session_id: str) -> list:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Chat session ID
            
        Returns:
            List of message dicts
        """
        messages = self.db.get_session_history(session_id)
        
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "message": msg.message,
                "resolved_query": msg.resolved_query,
                "entities": msg.entities_mentioned,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
            })
        
        return history
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear all messages in a session.
        
        Args:
            session_id: Chat session ID
            
        Returns:
            bool: Success status
        """
        return self.db.clear_session(session_id)
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: Chat session ID
            
        Returns:
            bool: True if session exists
        """
        return self.db.session_exists(session_id)
