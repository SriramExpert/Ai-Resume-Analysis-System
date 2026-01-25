from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import shutil
import os
import json
from src.tools.tool1_resume_parser import ResumeParser
from src.tools.tool2_comparison_engine import ComparisonEngine
from src.tools.tool3_blog_generator import BlogGenerator
from src.utils.db_handler import PostgresHandler
from src.utils.vector_db import VectorDBHandler
from src.utils.context_resolver import ContextResolver
from src.utils.chat_manager import ChatHistoryManager
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Resume Analysis System API")

# Initialize Tools and Handlers
parser_tool = ResumeParser("config/config.yaml")
comparison_tool = ComparisonEngine("config/config.yaml")
blog_tool = BlogGenerator("config/config.yaml")
db_handler = PostgresHandler()
vector_db = VectorDBHandler()

# In your server.py, after initializing vector_db:
#vector_db.debug_collection_info()

# Initialize Chat Context System
context_resolver = ContextResolver(parser_tool.llm_handler, db_handler)
chat_manager = ChatHistoryManager(db_handler, context_resolver)



# 👇 ADD CORS RIGHT HERE
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
os.makedirs("data/resumes/uploads", exist_ok=True)

class ProcessRequest(BaseModel):
    query: str  # User prompt like "Compare Sriram and Raju"

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None  # Auto-create if not provided


@app.post("/api/upload")
async def upload_resumes(files: List[UploadFile] = File(...)):
    """Upload, parse, chunk, and store resumes in both DBs."""
    results = []
    for file in files:
        try:
            temp_path = f"data/resumes/uploads/{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Parse, Chunk, and Store (handled inside ResumeParser now)
            data = parser_tool.process_resume(temp_path)
            name = data.get('name', file.filename)
            
            results.append({"filename": file.filename, "candidate": name, "status": "success"})
        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "message": str(e)})
            
    return {"message": f"Processed {len(results)} files.", "details": results}

@app.get("/api/candidates")
async def list_candidates():
    """List all currently stored candidates from PostgreSQL."""
    resumes = db_handler.get_all_resumes()
    return {"candidates": [r.candidate_name for r in resumes]}

@app.post("/api/process")
async def process_request(request: ProcessRequest):
    """
    Unified endpoint using Router LLM to detect tool and execute.
    """
    query = request.query
    
    # 1. ROUTER: Detect which tool to call
    tool_id = parser_tool.llm_handler.route_query(query)
    
    # Fetch all resumes for tools that need context
    stored_resumes = db_handler.get_all_resumes()
    resumes_data_list = [r.parsed_json for r in stored_resumes]
    
    if not resumes_data_list and tool_id != "ask":
        raise HTTPException(status_code=400, detail="No resumes in database. Please upload first.")

    # 2. EXECUTE based on tool_id
    try:
        if tool_id == "ask":
            # Role 3: Response LLM + ChromaDB (RAG)
            # Search ChromaDB for relevant chunks across all resumes
            search_results = vector_db.query(query, n_results=5)
            context_chunks = search_results.get('documents', [[]])[0]
            context = "\n---\n".join(context_chunks)
            
            answer = parser_tool.llm_handler.generate_response(query, context)
            
            # Log to DB
            db_handler.log_query(query, "ask", answer)
            
            return {
                "tool_detected": "ask",
                "query": query,
                "response": answer,
                "source_count": len(context_chunks)
            }

        elif tool_id == "stats":
            # Role 1: Statistics LLM
            stats = parser_tool.llm_handler.analyze_statistics(resumes_data_list)
            
            # Also calculate traditional metrics for charts
            performance = comparison_tool.calculate_performance_metrics(resumes_data_list)
            
            response_data = {
                "tool_detected": "stats",
                "ai_insights": stats,
                "performance_metrics": performance,
                "chart_data": {
                    "type": "radar",
                    "labels": ["Technical", "Experience", "Education", "Diversity"],
                    "datasets": [
                        {
                            "label": p["name"],
                            "data": [p["scores"]["Technical"], p["scores"]["Experience"], 
                                     p["scores"]["Education"], p["scores"]["Diversity"]]
                        } for p in performance
                    ]
                }
            }
            db_handler.log_query(query, "stats", "Stats generated successfully")
            return response_data

        elif tool_id == "compare":
            if len(resumes_data_list) < 2:
                raise HTTPException(status_code=400, detail="Need at least 2 resumes for comparison.")
            
            comparison = comparison_tool.compare_resumes(resumes_data_list)
            db_handler.log_query(query, "compare", "Comparison generated")
            return {"tool_detected": "compare", "data": comparison}

        elif tool_id == "blog":
            if not resumes_data_list:
                raise HTTPException(status_code=400, detail="No resumes for blog generation.")
                
            comparison = comparison_tool.compare_resumes(resumes_data_list)
            blog_content = blog_tool.generate_blog_post(comparison, resumes_data_list)
            db_handler.log_query(query, "blog", "Blog generated")
            return {
                "tool_detected": "blog",
                "title": "Resume Analysis Report",
                "content": blog_content
            }

    except Exception as e:
        db_handler.log_query(query, tool_id, f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.delete("/api/clear")
async def clear_store():
    """Clear all stored resumes (WIP: needs proper DB clear logic)."""
    # For simplicity, we just clear ChromaDB for now
    vector_db.clear_all()
    # Postgres clearing would need a DELETE FROM query
    return {"message": "ChromaDB cleared. Note: PostgreSQL metadata remains."}


# ===== Chat Context Endpoints =====

@app.post("/api/chat/new-session")
async def create_chat_session():
    """Create a new chat session for context-aware conversations."""
    session_id = chat_manager.create_new_session()
    return {
        "session_id": session_id,
        "message": "New chat session created"
    }

@app.post("/api/chat/query")
async def chat_query(request: ChatRequest):
    """
    Process query with chat history context.
    Automatically resolves pronouns and implicit references.
    """
    try:
        print(f"\n{'='*60}")
        print(f"ORIGINAL QUERY: {request.query}")
        print(f"SESSION ID: {request.session_id}")
        
        # Process message with context resolution
        result = chat_manager.process_message(request.query, request.session_id)
        
        session_id = result['session_id']
        resolved_query = result['resolved_query']
        
        print(f"RESOLVED QUERY: {resolved_query}")
        print(f"CONTEXT APPLIED: {result['context_applied']}")
        print(f"ENTITIES DETECTED: {result.get('entities', [])}")
        print(f"CONFIDENCE: {result.get('confidence', 0.0)}")
        print(f"{'='*60}\n")
        
        # Use resolved query for tool execution
        tool_id = parser_tool.llm_handler.route_query(resolved_query)
        print(f"TOOL DETECTED: {tool_id}")
        
        # Fetch all resumes for tools that need context
        stored_resumes = db_handler.get_all_resumes()
        resumes_data_list = [r.parsed_json for r in stored_resumes]
        
        if not resumes_data_list and tool_id != "ask":
            raise HTTPException(status_code=400, detail="No resumes in database. Please upload first.")
        
        # Execute based on tool_id
        response_data = None
        
        if tool_id == "ask":
            # ===== ADD THIS HELPER FUNCTION =====
            def find_candidate_match(query_name: str, all_candidates: list) -> str:
                """Find the best matching candidate name from database"""
                if not query_name:
                    return None
                
                query_lower = query_name.lower().strip()
                all_candidate_names = [c.candidate_name for c in all_candidates]
                
                print(f"  Looking for match for: '{query_name}'")
                print(f"  Among candidates: {all_candidate_names}")
                
                # Try exact match (case-insensitive)
                for candidate in all_candidates:
                    if candidate.candidate_name.lower() == query_lower:
                        print(f"  ✓ Exact match found: {candidate.candidate_name}")
                        return candidate.candidate_name
                
                # Try partial match (e.g., "sriram" matches "SRIRAM P")
                for candidate in all_candidates:
                    candidate_lower = candidate.candidate_name.lower()
                    if query_lower in candidate_lower:
                        print(f"  ✓ Partial match: '{query_name}' in '{candidate.candidate_name}'")
                        return candidate.candidate_name
                
                # Try matching first name only
                query_first = query_lower.split()[0] if ' ' in query_lower else query_lower
                for candidate in all_candidates:
                    candidate_first = candidate.candidate_name.lower().split()[0]
                    if query_first == candidate_first:
                        print(f"  ✓ First name match: '{query_first}' matches '{candidate.candidate_name}'")
                        return candidate.candidate_name
                
                print(f"  ✗ No match found for '{query_name}'")
                return None
            # ===== END HELPER FUNCTION =====
            
            # DEBUG: Check if we have a candidate name
            candidate_name = None
            all_candidates = list(stored_resumes)  # Get actual objects
            
            for entity in result.get('entities', []):
                entity_type = entity.get('type', '').lower()
                entity_name = entity.get('name', '')
                
                print(f"ENTITY: name='{entity_name}', type='{entity_type}', is_pronoun={entity.get('is_pronoun', False)}")
                
                # Look for candidate names
                if not entity.get('is_pronoun', False) and entity_name:
                    # Use the helper function to find match
                    matched = find_candidate_match(entity_name, all_candidates)
                    if matched:
                        candidate_name = matched
                        break
            
            print(f"CANDIDATE NAME EXTRACTED: {candidate_name}")
            
            # RAG query with ChromaDB - filter by candidate if we found one
            if candidate_name:
                # Try to find the candidate in our database
                print(f"Searching vector DB for candidate: {candidate_name}")
                search_results = vector_db.query(resolved_query, n_results=5, candidate_name=candidate_name)
            else:
                # Search across all candidates
                print(f"No specific candidate, searching all resumes")
                search_results = vector_db.query(resolved_query, n_results=5)
            
            context_chunks = search_results.get('documents', [[]])[0]
            context = "\n---\n".join(context_chunks)
            
            print(f"CONTEXT CHUNKS FOUND: {len(context_chunks)}")
            if context_chunks:
                print(f"SAMPLE CHUNK: {context_chunks[0][:100]}...")
            
            # DEBUG: If no context found, show what's in vector DB
            if len(context_chunks) == 0:
                print(f"⚠️ No context chunks found!")
                print(f"Trying to see what's in vector DB...")
                
                # Try a generic search to see if ANYTHING is in vector DB
                test_results = vector_db.query("", n_results=3)
                if test_results and 'documents' in test_results:
                    total_docs = len(test_results['documents'][0]) if test_results['documents'][0] else 0
                    print(f"Total documents in vector DB: {total_docs}")
                    
                    if total_docs > 0:
                        print("Showing available chunks:")
                        for i, doc in enumerate(test_results['documents'][0]):
                            print(f"  {i+1}. {doc[:80]}...")
            
            answer = parser_tool.llm_handler.generate_response(resolved_query, context)
            
            response_data = {
                "tool_detected": "ask",
                "response": answer,
                "source_count": len(context_chunks)
            }
            
        elif tool_id == "stats":
            stats = parser_tool.llm_handler.analyze_statistics(resumes_data_list)
            performance = comparison_tool.calculate_performance_metrics(resumes_data_list)
            
            response_data = {
                "tool_detected": "stats",
                "ai_insights": stats,
                "performance_metrics": performance
            }
            
        elif tool_id == "compare":
            if len(resumes_data_list) < 2:
                raise HTTPException(status_code=400, detail="Need at least 2 resumes for comparison.")
            
            comparison = comparison_tool.compare_resumes(resumes_data_list)
            response_data = {"tool_detected": "compare", "data": comparison}
            
        elif tool_id == "blog":
            if not resumes_data_list:
                raise HTTPException(status_code=400, detail="No resumes for blog generation.")
            
            comparison = comparison_tool.compare_resumes(resumes_data_list)
            blog_content = blog_tool.generate_blog_post(comparison, resumes_data_list)
            response_data = {
                "tool_detected": "blog",
                "title": "Resume Analysis Report",
                "content": blog_content
            }
        
        # Save assistant response to chat history
        if response_data:
            # Persist entities from the resolution/response context
            persistence_entities = result.get('entities', [])
            
            chat_manager.save_assistant_response(
                session_id,
                str(response_data.get('response', response_data)),
                entities=persistence_entities
            )
        
        # Return combined response
        return {
            "session_id": session_id,
            "original_query": result['original_query'],
            "resolved_query": resolved_query,
            "context_applied": result['context_applied'],
            "confidence": result['confidence'],
            "entities_used": result.get('entities', []),
            **response_data
        }
        
    except Exception as e:
        import traceback
        print(f"ERROR in chat_query: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing chat query: {str(e)}")


@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Retrieve conversation history for a session."""
    if not chat_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    history = chat_manager.get_session_history(session_id)
    return {
        "session_id": session_id,
        "messages": history,
        "message_count": len(history)
    }


@app.delete("/api/chat/clear/{session_id}")
async def clear_chat_session(session_id: str):
    """Clear all messages in a chat session."""
    if not chat_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    success = chat_manager.clear_session(session_id)
    if success:
        return {"message": f"Session {session_id} cleared successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear session")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
