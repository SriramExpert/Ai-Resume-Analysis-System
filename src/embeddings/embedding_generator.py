import numpy as np
from typing import List, Dict, Any, Tuple
from fastembed import TextEmbedding
import hashlib
import json

class EmbeddingGenerator:
    """Generate embeddings for resumes using FastEmbed"""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model = TextEmbedding(model_name=model_name)
    
    def generate_document_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for entire document"""
        # fastembed.embed returns a generator, we take the first element
        return next(self.model.embed([text]))
    
    def generate_query_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a query"""
        # For BGE, document and query embeddings are often the same, 
        # but adding this for API compatibility
        return self.generate_document_embedding(text)
    
    def generate_section_embeddings(self, resume_data: Dict) -> Dict[str, np.ndarray]:
        """Generate embeddings for different sections"""
        embeddings = {}
        
        # Whole resume text embedding
        full_text = self._compile_full_text(resume_data)
        embeddings['full_document'] = self.generate_document_embedding(full_text)
        
        # Tech stack embedding
        tech_text = " ".join(resume_data.get('tech_stack', []))
        if tech_text:
            embeddings['tech_stack'] = next(self.model.embed([tech_text]))
        
        # Experience embedding
        exp_text = " ".join([
            f"{exp.get('title', '')} at {exp.get('company', '')}: {exp.get('description', '')}"
            for exp in resume_data.get('experience', [])
        ])
        if exp_text:
            embeddings['experience'] = next(self.model.embed([exp_text]))
        
        # Skills embedding
        skills_text = self._compile_skills_text(resume_data.get('skills', {}))
        if skills_text:
            embeddings['skills'] = next(self.model.embed([skills_text]))
        
        return embeddings
    
    def compute_similarity_matrix(self, embeddings_list: List[Dict]) -> np.ndarray:
        """Compute similarity matrix between all resumes"""
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Use full document embeddings for overall similarity
        doc_embeddings = [emb['full_document'] for emb in embeddings_list]
        
        # Compute similarity matrix
        similarity_matrix = cosine_similarity(doc_embeddings)
        
        return similarity_matrix
    
    def find_similar_skills(self, embeddings_list: List[Dict], threshold: float = 0.8) -> Dict:
        """Find similar skills across candidates"""
        # This is a simplified version - in production, you'd want more sophisticated matching
        similarities = {}
        
        for i in range(len(embeddings_list)):
            for j in range(i + 1, len(embeddings_list)):
                sim = cosine_similarity(
                    [embeddings_list[i]['skills']],
                    [embeddings_list[j]['skills']]
                )[0][0]
                
                if sim > threshold:
                    key = f"candidate_{i+1}_candidate_{j+1}"
                    similarities[key] = float(sim)
        
        return similarities
    
    def _compile_full_text(self, resume_data: Dict) -> str:
        """Compile structured data into text for embedding"""
        sections = []
        
        sections.append(f"Summary: {resume_data.get('summary', '')}")
        
        for exp in resume_data.get('experience', []):
            sections.append(f"{exp.get('title', '')} at {exp.get('company', '')}: {exp.get('description', '')}")
        
        sections.append(f"Skills: {self._compile_skills_text(resume_data.get('skills', {}))}")
        
        return " ".join(sections)
    
    def _compile_skills_text(self, skills: Dict) -> str:
        """Compile skills dictionary into text"""
        skill_texts = []
        for category, items in skills.items():
            if items:
                skill_texts.append(f"{category}: {', '.join(items)}")
        return ". ".join(skill_texts)