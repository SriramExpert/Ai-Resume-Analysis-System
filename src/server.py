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

app = FastAPI(title="Resume Analysis System API")

# Initialize Tools
parser_tool = ResumeParser("config/config.yaml")
comparison_tool = ComparisonEngine("config/config.yaml")
blog_tool = BlogGenerator("config/config.yaml")

# In-Memory Data Store
# Keys are candidate names or filenames, Values are the parsed data
resume_store: Dict[str, Dict[str, Any]] = {}

# Ensure upload directory exists
os.makedirs("data/resumes/uploads", exist_ok=True)

class QuestionRequest(BaseModel):
    candidate_name: str
    question: str

@app.post("/api/upload")
async def upload_resumes(files: List[UploadFile] = File(...)):
    """Upload and parse resumes, storing them in memory for further use."""
    results = []
    for file in files:
        try:
            temp_path = f"data/resumes/uploads/{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Parse
            data = parser_tool.process_resume(temp_path)
            
            # Store by name (or filename if name is unknown)
            name = data.get('name', file.filename)
            resume_store[name] = data
            
            results.append({"filename": file.filename, "candidate": name, "status": "success"})
        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "message": str(e)})
            
    return {"message": f"Processed {len(results)} files.", "details": results}

@app.get("/api/candidates")
async def list_candidates():
    """List all currently uploaded candidates."""
    return {"candidates": list(resume_store.keys())}

@app.post("/api/tool1/ask")
async def ask_question(request: QuestionRequest):
    """Tool 1: Ask a question about a specific stored resume."""
    name_query = request.candidate_name.strip().lower()
    
    # 1. Exact or case-insensitive name match
    found_key = None
    for key in resume_store.keys():
        if key.lower() == name_query:
            found_key = key
            break
            
    # 2. Try matching original filename (if we stored it)
    if not found_key:
        for key, data in resume_store.items():
            source = data.get('source_file', '').lower()
            if name_query in source:
                found_key = key
                break
                
    # 3. Try partial name match
    if not found_key:
        for key in resume_store.keys():
            if name_query in key.lower():
                found_key = key
                break

    if not found_key:
        available = list(resume_store.keys())
        raise HTTPException(status_code=404, detail={
            "error": f"Candidate '{request.candidate_name}' not found.",
            "available_candidates": available,
            "suggestion": "Check the spelling or use the name exactly as it appears in the list."
        })
        
    data = resume_store[found_key]
    answers = parser_tool.answer_questions(data, [request.question])
    
    return {
        "candidate_found": found_key,
        "question": request.question,
        "answer": answers.get(request.question, "No answer generated.")
    }

@app.post("/api/tool2/blog")
async def generate_blog():
    """Tool 2: Generate a blog post comparing all stored resumes."""
    if len(resume_store) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 resumes to generate a comparison blog.")
        
    resumes_list = list(resume_store.values())
    
    try:
        # We need a comparison first to generate the blog
        comparison = comparison_tool.compare_resumes(resumes_list)
        blog_content = blog_tool.generate_blog_post(comparison, resumes_list)
        
        return {
            "title": "Resume Comparison Blog Post",
            "content": blog_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating blog: {str(e)}")

@app.post("/api/tool3/compare")
async def compare_resumes():
    """Tool 3: Compare all stored resumes and return metrics."""
    if len(resume_store) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 resumes for comparison.")
        
    resumes_list = list(resume_store.values())
    
    try:
        comparison = comparison_tool.compare_resumes(resumes_list)
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during comparison: {str(e)}")

@app.delete("/api/clear")
async def clear_store():
    """Clear all stored resumes."""
    resume_store.clear()
    return {"message": "Data store cleared."}

@app.post("/api/tool4/stats")
async def get_statistics():
    """Tool 4: Generate performance statistics and visual data."""
    if not resume_store:
        raise HTTPException(status_code=400, detail="No resumes uploaded. Please upload first.")
        
    resumes_list = list(resume_store.values())
    
    try:
        # Calculate scores
        performance = comparison_tool.calculate_performance_metrics(resumes_list)
        
        # Calculate similarity (if multiple)
        similarity_data = {}
        if len(resumes_list) >= 2:
            comparison = comparison_tool.compare_resumes(resumes_list)
            similarity_data = comparison.get('similarity_analysis', {})

        return {
            "performance_metrics": performance,
            "comparison_summary": similarity_data,
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating statistics: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
