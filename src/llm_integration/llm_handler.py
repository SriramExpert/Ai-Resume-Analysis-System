import os
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

from src.utils.file_handlers import FileHandler

class LLMHandler:
    """Handle LLM interactions"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = FileHandler.load_config(config_path)
        llm_config = self.config.get('llm', {})
        self.provider = llm_config.get('provider', 'openai')
        self.model = llm_config.get('model', 'gpt-4-1106-preview')
        self.temperature = llm_config.get('temperature', 0.1)
        
        if self.provider == 'openai':
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        else:
            self.client = None

    def extract_resume_info(self, resume_text: str) -> Dict[str, Any]:
        """Extract structured information from resume text using LLM"""
        if not self.client:
            raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")

        prompt = f"""
        You are an expert Resume Parser. Extract the following information from the resume text below into a valid JSON object:
        - name (string)
        - email (string)
        - phone (string)
        - summary (string)
        - skills (dictionary with keys: programming_languages, frameworks, tools, databases)
        - experience (list of objects: title, company, description, dates)
        - education (list of objects: degree, institution, year)
        - tech_stack (list of strings - all technical keywords found)
        
        Resume Text:
        {resume_text[:4000]}  # Truncate to avoid token limits if necessary
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You look for structured data in resumes. Output ONLY JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            data = json.loads(response.choices[0].message.content)
            return data
        except Exception as e:
            print(f"Error in extract_resume_info: {e}")
            return {"error": str(e), "raw_text": resume_text[:100]}

    def compare_resumes(self, resumes_data: List[Dict]) -> Dict[str, Any]:
        """Compare resumes using LLM"""
        if not self.client:
            return {"error": "No OpenAI Client"}
            
        candidates_json = json.dumps([{k: v for k, v in r.items() if k != 'source_file'} for r in resumes_data], indent=2)
        
        prompt = f"""
        Compare the following candidates based on their resume data. 
        Provide a detailed analysis in JSON format with the following keys:
        - summary (object with: most_experienced, most_diverse_skills, overall_verdict)
        - tech_stack_comparison (object with: common_technologies, unique_technologies_by_candidate)
        - strengths_weaknesses (dictionary where key is candidate name and value is object with strengths=[], weaknesses=[])
        - recommendations (dictionary where key is a potential job role and value is the best candidate name)
        
        Candidates Data:
        {candidates_json}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a Technical Recruiter comparing candidates. Output ONLY JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error in compare_resumes: {e}")
            return {"error": str(e)}

    def generate_blog_post(self, comparison_data: Dict, resumes_data: List[Dict]) -> str:
        """Generate blog post using LLM"""
        if not self.client:
            return "Error: OpenAI client not available."
            
        context = json.dumps({
            "comparison": comparison_data,
            "candidates": [r.get('name') for r in resumes_data]
        }, indent=2)
        
        prompt = f"""
        Write a professional technical blog post comparing these candidates.
        Use Markdown formatting.
        Include:
        - An engaging title
        - Executive summary
        - Detailed technical comparison
        - Strengths of each candidate
        - Final recommendation
        
        Context Data:
        {context}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a Technical Writer creating a hiring report."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating blog: {str(e)}"
        
    def answer_questions(self, resume_data: Dict, questions: List[str]) -> Dict[str, str]:
        """Answer specific questions"""
        if not self.client:
            return {q: "Error: No API Key" for q in questions}
            
        resume_context = json.dumps(resume_data, indent=2)
        answers = {}
        
        for q in questions:
            prompt = f"""
            Based on the resume data below, answer the question: "{q}"
            Keep the answer concise (under 50 words).
            
            Resume Data:
            {resume_context}
            """
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an assistant answering questions about a candidate."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                answers[q] = response.choices[0].message.content
            except Exception as e:
                answers[q] = f"Error: {str(e)}"
                
        return answers

load_dotenv()