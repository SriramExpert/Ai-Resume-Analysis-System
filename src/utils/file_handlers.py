import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import PyPDF2
import pdfplumber
import docx

class FileHandler:
    """Handle file operations for resume processing"""
    
    @staticmethod
    def read_pdf(file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        
        try:
            # Try with pdfplumber first (better for formatted text)
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except:
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                raise Exception(f"Failed to read PDF: {str(e)}")
        
        return text.strip()
    
    @staticmethod
    def read_docx(file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except Exception as e:
            raise Exception(f"Failed to read DOCX: {str(e)}")
    
    @staticmethod
    def read_txt(file_path: str) -> str:
        """Read text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            raise Exception(f"Failed to read text file: {str(e)}")
    
    @staticmethod
    def read_resume(file_path: str) -> str:
        """Read resume file based on extension"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return FileHandler.read_pdf(file_path)
        elif ext == '.docx':
            return FileHandler.read_docx(file_path)
        elif ext == '.txt' or ext == '.md':
            return FileHandler.read_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    @staticmethod
    def save_json(data: Dict, file_path: str):
        """Save data as JSON file"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def load_json(file_path: str) -> Dict:
        """Load JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def save_embeddings(embeddings: List, file_path: str):
        """Save embeddings as numpy file"""
        import numpy as np
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        np.save(file_path, np.array(embeddings))
    
    @staticmethod
    def load_embeddings(file_path: str):
        """Load embeddings from numpy file"""
        import numpy as np
        return np.load(file_path)
    
    @staticmethod
    def load_config(config_path: str = "config/config.yaml") -> Dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)