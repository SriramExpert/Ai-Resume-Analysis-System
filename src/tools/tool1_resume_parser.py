import os
import json
from typing import Dict, List, Any
from datetime import datetime

from src.utils.file_handlers import FileHandler
from src.llm_integration.llm_handler import LLMHandler

class ResumeParser:
    """Tool 1: Parse resumes and extract information"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = FileHandler.load_config(config_path)
        self.llm_handler = LLMHandler(config_path)
        self.file_handler = FileHandler()
        
    def process_multiple_resumes(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple resume files"""
        results = []
        for file_path in file_paths:
            if os.path.exists(file_path):
                try:
                    data = self.process_resume(file_path)
                    results.append(data)
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
        return results
        
    def process_resume(self, file_path: str) -> Dict[str, Any]:
        """Process a single resume file"""
        # 1. Read file content
        text = self.file_handler.read_resume(file_path)
        
        # 2. Extract information using LLM
        extracted_data = self.llm_handler.extract_resume_info(text)
        
        # 3. Add metadata
        extracted_data['source_file'] = file_path
        extracted_data['processed_date'] = datetime.now().isoformat()
        
        return extracted_data

    def answer_questions(self, resume_data: Dict, questions: List[str]) -> Dict[str, str]:
        """Answer specific questions about a resume"""
        return self.llm_handler.answer_questions(resume_data, questions)