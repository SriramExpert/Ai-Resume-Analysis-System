import os
import json
from typing import Dict, List, Any
from datetime import datetime

from src.utils.file_handlers import FileHandler
from src.llm_integration.llm_handler import LLMHandler
from src.utils.db_handler import PostgresHandler
from src.utils.vector_db import VectorDBHandler
from src.embeddings.embedding_generator import EmbeddingGenerator

class ResumeParser:
    """Tool 1: Parse resumes and extract information"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = FileHandler.load_config(config_path)
        self.llm_handler = LLMHandler(config_path)
        self.file_handler = FileHandler()
        self.db_handler = PostgresHandler()
        self.vector_db = VectorDBHandler()
        self.embedding_generator = EmbeddingGenerator()
        
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
        """Process a single document file and store in DBs"""
        # 1. Read file content
        text = self.file_handler.read_resume(file_path)
        
        # 2. Extract information using LLM
        extracted_data = self.llm_handler.extract_resume_info(text)
        
        # 3. Add metadata (Handle generic documents)
        # Fallback to filename if LLM doesn't find a name (common in generic docs)
        filename_base = os.path.splitext(os.path.basename(file_path))[0]
        name = extracted_data.get('candidate_name') or extracted_data.get('name') or extracted_data.get('subject_name') or filename_base
        
        # Ensure name is set in data
        extracted_data['candidate_name'] = name
        extracted_data['source_file'] = file_path
        extracted_data['processed_date'] = datetime.now().isoformat()
        
        # 4. CHUNK and store in ChromaDB
        chunks = self._chunk_text(text)
        # Use filename as backup for ID generation if name is too generic? No, name is fine.
        self.vector_db.add_resume_chunks(name, chunks)
        
        # 5. Store metadata in PostgreSQL
        self.db_handler.save_metadata(name, file_path, extracted_data)
        
        return extracted_data

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks by paragraphs when possible"""
        if not text:
            return []
            
        # Try to split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for p in paragraphs:
            if len(current_chunk) + len(p) < chunk_size:
                current_chunk += p + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If a single paragraph is larger than chunk_size, split it by characters
                if len(p) > chunk_size:
                    for i in range(0, len(p), chunk_size - overlap):
                        chunks.append(p[i:i + chunk_size])
                    current_chunk = ""
                else:
                    current_chunk = p + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    def answer_questions(self, resume_data: Dict, questions: List[str]) -> Dict[str, str]:
        """Answer specific questions about a resume"""
        return self.llm_handler.answer_questions(resume_data, questions)
