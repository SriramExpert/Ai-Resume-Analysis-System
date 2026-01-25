import os
import json
import traceback
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
import google.genai as genai
from google.genai.types import GenerateContentConfig
from src.utils.file_handlers import FileHandler

class LLMHandler:
    """Handle LLM interactions"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = FileHandler.load_config(config_path)
        llm_config = self.config.get('llm', {})
        
        self.provider = llm_config.get('provider', 'openai')
        self.model_name = llm_config.get('model')
        self.temperature = llm_config.get('temperature', 0.1)
        self.client = None

        if self.provider == 'openai':
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        elif self.provider == 'gemini':
            # Initialize Gemini client
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment variables")
            
            # Create client
            self.client = genai.Client(
                api_key=api_key,
                http_options={'api_version': 'v1'}
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _call_llm(self, prompt: str, system_prompt: str = None, response_format: str = "text", **kwargs) -> Any:
        """Unified method to call LLM with provider-specific implementations"""
        try:
            temperature = kwargs.get('temperature', 0.1)
            
            if self.provider == 'openai':
                if not self.client:
                    raise ValueError("OpenAI client not initialized")
                
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                if response_format == "json_object":
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        response_format={"type": "json_object"},
                        temperature=temperature
                    )
                    return json.loads(response.choices[0].message.content)
                else:
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=temperature
                    )
                    return response.choices[0].message.content
                
            elif self.provider == 'gemini':
                if not self.client:
                    raise ValueError("Gemini client not properly initialized")

                # Simplified Gemini implementation
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                else:
                    full_prompt = prompt
                
                if response_format == "json_object":
                    full_prompt = f"{full_prompt}\n\nOutput ONLY valid JSON."
                
                # Use gemini-2.0-flash by default as fallback, or configured model
                model_to_use = self.model_name if self.model_name else "models/gemini-2.0-flash"
                if not model_to_use.startswith('models/'):
                    model_to_use = f"models/{model_to_use}"

                response = self.client.models.generate_content(
                    model=model_to_use,
                    contents=[full_prompt],
                    config=GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=8192
                    )
                )
                
                result = response.text
                
                if response_format == "json_object":
                    try:
                        # Try to parse JSON
                        return json.loads(result)
                    except json.JSONDecodeError:
                        # Try to clean and parse
                        import re
                        # Remove markdown code blocks
                        cleaned = re.sub(r'```(?:json)?\s*|\s*```', '', result)
                        try:
                            return json.loads(cleaned)
                        except:
                            # Find JSON object pattern
                            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                            if match:
                                try:
                                    return json.loads(match.group())
                                except:
                                    pass
                            return {"text": result, "parse_error": "Could not parse as JSON", "document_type": "unknown", "candidate_name": "Unknown"}
                
                return result
                
        except Exception as e:
            print(f"Error in _call_llm: {e}")
            print(traceback.format_exc())
            raise

    def extract_resume_info(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract structured information from resume text using LLM.
        """
        # Ensure resume_text is not empty
        if not resume_text or len(resume_text.strip()) < 10:
            return {
                "error": "Resume text is too short or empty",
                "document_type": "unknown", 
                "candidate_name": "Unknown"
            }
        
        prompt = f"""
        Extract structured information from this resume text:
        
        {resume_text[:5000]}
        
        Return a JSON object with these fields:
        - candidate_name (string)
        - document_type (string, e.g., "Software Engineer Resume")
        - contact_info (object with email, phone, location, linkedin if available)
        - summary (string, brief professional summary)
        - tech_stack (list of strings, technical skills)
        - experience (list of objects with title, company, period)
        - education (list of objects with degree, institution, year)
        
        If information is missing, use empty strings or lists.
        """
        
        try:
            system_prompt = "You are a resume parser. Extract information accurately. Output ONLY valid JSON."
            result = self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="json_object",
                temperature=0.0
            )
            
            # Ensure the result has required fields
            if isinstance(result, dict):
                if "candidate_name" not in result:
                    result["candidate_name"] = "Unknown"
                if "document_type" not in result:
                    result["document_type"] = "Resume"
                return result
            else:
                return {
                    "error": "Unexpected response format",
                    "document_type": "unknown", 
                    "candidate_name": "Unknown"
                }
                
        except Exception as e:
            print(f"Error in extract_resume_info: {e}")
            print(traceback.format_exc())
            return {
                "error": str(e), 
                "document_type": "unknown", 
                "candidate_name": "Unknown"
            }

    # [Keep all other methods - they should use self._call_llm()]


    def compare_resumes(self, resumes_data: List[Dict]) -> Dict[str, Any]:
        """Compare resumes using LLM"""
        if not self.client:
            return {"error": "No LLM Client"}
            
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
            system_prompt = "You are a Technical Recruiter comparing candidates. Output ONLY JSON."
            return self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="json_object",
                temperature=0.2
            )
        except Exception as e:
            print(f"Error in compare_resumes: {e}")
            return {"error": str(e)}

    def generate_blog_post(self, comparison_data: Dict, resumes_data: List[Dict]) -> str:
        """Generate blog post using LLM"""
        if not self.client:
            return "Error: LLM client not available."
            
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
            system_prompt = "You are a Technical Writer creating a hiring report. Use Markdown formatting."
            return self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="text",
                temperature=0.7
            )
        except Exception as e:
            return f"Error generating blog: {str(e)}"

    def answer_questions(self, resume_data: Dict, questions: List[str]) -> Dict[str, str]:
        """Answer specific questions with improved formatting"""
        if not self.client:
            return {q: "Error: No API Key" for q in questions}
        
        # Pre-process questions to detect query type
        answers = {}
        
        for question in questions:
            query_type = self._detect_query_type(question)
            answer = self._answer_specific_query(question, resume_data, query_type)
            answers[question] = answer
        
        return answers

    def _detect_query_type(self, query: str) -> str:
        """Detect what type of information is being asked for"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['skill', 'tech', 'technology', 'language', 'framework']):
            return 'skillset'
        elif any(word in query_lower for word in ['experience', 'work', 'job', 'role', 'position', 'company']):
            return 'experience'
        elif any(word in query_lower for word in ['education', 'degree', 'university', 'college', 'school']):
            return 'education'
        elif any(word in query_lower for word in ['summary', 'overview', 'about', 'profile']):
            return 'summary'
        elif any(word in query_lower for word in ['project', 'work sample', 'portfolio']):
            return 'projects'
        elif any(word in query_lower for word in ['contact', 'email', 'phone', 'address', 'location']):
            return 'contact'
        elif any(word in query_lower for word in ['certification', 'certificate', 'cert']):
            return 'certifications'
        else:
            return 'general'

    def _answer_specific_query(self, query: str, resume_data: Dict, query_type: str) -> str:
        """Generate query-specific formatted responses"""
        
        # Different prompts for different query types
        prompts = {
            'skillset': self._create_skillset_prompt(query, resume_data),
            'experience': self._create_experience_prompt(query, resume_data),
            'education': self._create_education_prompt(query, resume_data),
            'summary': self._create_summary_prompt(query, resume_data),
            'projects': self._create_projects_prompt(query, resume_data),
            'contact': self._create_contact_prompt(query, resume_data),
            'certifications': self._create_certifications_prompt(query, resume_data),
            'general': self._create_general_prompt(query, resume_data)
        }
        
        prompt = prompts.get(query_type, self._create_general_prompt(query, resume_data))
        
        try:
            system_prompt = "You are a precise resume information assistant. Provide concise, well-formatted answers."
            return self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="text",
                temperature=0.2
            )
        except Exception as e:
            return f"Error: {str(e)}"

    # [Keep all the _create_*_prompt methods exactly as they were]

    def route_query(self, query: str) -> str:
        """Role 2: Router LLM - Detect which tool to call"""
        if not self.client:
            return "ask"
            
        prompt = f"""
        Analyze the user query and determine which tool to call.
        Options:
        - "ask": For specific questions about a candidate (e.g., "What are Sriram's skills?", "Where did Raju work?")
        - "compare": For comparing two or more candidates (e.g., "Who is better between Sriram and Raju?", "Compare all candidates")
        - "blog": For generating a professional blog post or report (e.g., "Write a blog about these resumes", "Generate a hiring report")
        - "stats": For statistical analysis or performance metrics (e.g., "Give me stats of all candidates", "Show me technical vs experience scores")
        
        User Query: "{query}"
        
        Return ONLY the tool identifier: "ask", "compare", "blog", or "stats".
        """
        
        try:
            system_prompt = "You are a Query Router for a recruitment system. Output ONLY the tool name."
            response = self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="text",
                temperature=0.0
            )
            tool = response.strip().lower()
            return tool if tool in ["ask", "compare", "blog", "stats"] else "ask"
        except Exception as e:
            print(f"Error in route_query: {e}")
            return "ask"

    def analyze_statistics(self, resumes_data: List[Dict]) -> Dict[str, Any]:
        """Role 1: Statistics LLM - Extract and analyze metrics"""
        if not self.client:
            return {"error": "LLM client not available"}
            
        context = json.dumps([{
            "candidate": r.get('candidate_name') or r.get('name'),
            "document_type": r.get('document_type', 'Resume'),
            "data": {k: v for k, v in r.items() if k not in ['source_file', 'processed_date', 'candidate_name', 'name']}
        } for r in resumes_data], indent=2)
        
        prompt = f"""
        Perform a statistical analysis on the following candidate data.
        Provide scores from 1-100 for each candidate across these categories:
        - Technical Profile (skills, stack depth)
        - Experience Maturity (years, roles)
        - Educational Strength 
        - Skill Diversity
        
        Also identify the "Top Candidate" and "Market Fit" summary.
        
        Candidates Data:
        {context}
        """
        
        try:
            system_prompt = "You are a Data Analyst specializing in HR metrics. Output ONLY JSON."
            return self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="json_object",
                temperature=0.1
            )
        except Exception as e:
            print(f"Error in analyze_statistics: {e}")
            return {"error": str(e)}

    def generate_response(self, query: str, context: str) -> str:
        """Role 3: Response LLM - Synthesize final answer from context"""
        if not self.client:
            return "Context retrieved but LLM synthesis failed."
            
        prompt = f"""
        User Question: "{query}"
        
        Relevant Information from Resumes:
        {context}
        
        Provide a natural, professional response to the user based ONLY on the provided context.
        If the information is not in the context, say you don't have that information.
        """
        
        try:
            system_prompt = "You are a helpful recruitment assistant."
            return self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="text",
                temperature=0.3
            )
        except Exception as e:
            return f"Error generating response: {str(e)}"

load_dotenv()