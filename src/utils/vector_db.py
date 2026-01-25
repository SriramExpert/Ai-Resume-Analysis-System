import chromadb
from chromadb.config import Settings
import os
import numpy as np
from typing import List, Dict, Any

from src.embeddings.embedding_generator import EmbeddingGenerator

class VectorDBHandler:
    def __init__(self, persist_directory: str = "data/chroma_db"):
        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)

        self.embedder = EmbeddingGenerator()

        class BGEEmbeddingFunction:
            def __init__(self, generator):
                self.generator = generator

            def __call__(self, input: List[str]) -> List[List[float]]:
                """Called by ChromaDB for embedding documents"""
                print(f"DEBUG __call__: Received {len(input)} documents")
                embeddings = []
                for i, text in enumerate(input):
                    try:
                        # Get embedding
                        embedding = self.generator.generate_document_embedding(text)
                        
                        # Ensure it's numpy array
                        if not isinstance(embedding, np.ndarray):
                            print(f"WARNING: Document embedding is not numpy array: {type(embedding)}")
                            embedding = np.array(embedding)
                        
                        # Convert to list
                        embedding_list = embedding.tolist()
                        
                        # Double check it's a list
                        if not isinstance(embedding_list, list):
                            print(f"ERROR: tolist() didn't return list: {type(embedding_list)}")
                            embedding_list = [float(embedding_list)] * 384
                        
                        embeddings.append(embedding_list)
                        print(f"DEBUG __call__: Document {i} -> list length: {len(embedding_list)}")
                        
                    except Exception as e:
                        print(f"ERROR embedding document: {e}")
                        # Fallback: return zeros
                        embeddings.append([0.0] * 384)
                
                return embeddings
            
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                return self.__call__(input=texts)

            def embed_query(self, input: str) -> List[List[float]]:  # Changed return type
                """Embed a query - ChromaDB calls this"""
                print(f"DEBUG embed_query: Received input type: {type(input)}")
                
                # Extract query text
                if isinstance(input, list):
                    query_text = input[0] if input else ""
                else:
                    query_text = str(input)
                
                print(f"DEBUG embed_query: Query text: '{query_text[:50]}...'")
                
                try:
                    # Get embedding
                    embedding = self.generator.generate_query_embedding(query_text)
                    print(f"DEBUG embed_query: Raw embedding type: {type(embedding)}")
                    
                    # Ensure it's numpy array
                    if not isinstance(embedding, np.ndarray):
                        print(f"WARNING: Query embedding is not numpy array: {type(embedding)}")
                        embedding = np.array(embedding)
                    
                    # Convert to list
                    embedding_list = embedding.tolist()
                    print(f"DEBUG embed_query: After tolist() type: {type(embedding_list)}")
                    
                    # CRITICAL FIX: ChromaDB expects a list of lists, even for single query
                    # Wrap the list in another list
                    result = [embedding_list]  # This is the key fix!
                    print(f"DEBUG embed_query: Wrapped in list, final type: {type(result)}, inner length: {len(result[0])}")
                    
                    return result  # Return list of lists
                    
                except Exception as e:
                    print(f"ERROR in embed_query: {e}")
                    import traceback
                    traceback.print_exc()
                    # Return proper dummy embedding wrapped in list
                    return [[0.1] * 384]
            def name(self) -> str:
                return "bge-embedding-generator"

        self.embedding_function = BGEEmbeddingFunction(self.embedder)

        self.collection = self.client.get_or_create_collection(
            name="resumes",
            embedding_function=self.embedding_function
        )
        print("VectorDB initialized successfully")

    def add_resume_chunks(self, candidate_name: str, chunks: List[str], metadatas: List[Dict[str, Any]] = None):
        """Add chunks for a specific candidate"""
        ids = [f"{candidate_name}_{i}" for i in range(len(chunks))]
        if metadatas is None:
            metadatas = [{"candidate": candidate_name} for _ in range(len(chunks))]
        else:
            for m in metadatas:
                m["candidate"] = candidate_name
                
        print(f"Adding {len(chunks)} chunks for {candidate_name}")
        self.collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_text: str, n_results: int = 5, candidate_name: str = None) -> Dict[str, Any]:
        """Search for relevant chunks, optionally filtered by candidate"""
        where_filter = None
        if candidate_name:
            where_filter = {"candidate": candidate_name}
        
        print(f"Querying: '{query_text}'")
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter
            )
            print(f"Query successful, found {len(results['documents'][0]) if results['documents'] else 0} results")
            return results
        except Exception as e:
            print(f"Query error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def delete_candidate(self, candidate_name: str):
        """Remove all chunks for a candidate"""
        self.collection.delete(where={"candidate": candidate_name})
        
    def clear_all(self):
        """Wipe the collection"""
        self.client.delete_collection("resumes")
        self.collection = self.client.get_or_create_collection(
            name="resumes",
            embedding_function=self.embedding_function
        )