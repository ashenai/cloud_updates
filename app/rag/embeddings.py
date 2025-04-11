"""
RAG implementation for cloud updates using sentence transformers for embeddings
and FAISS for vector similarity search.
"""
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from typing import List, Dict, Tuple
from app.models import Update
from datetime import datetime

class UpdateEmbeddings:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.updates = []
        
    def create_update_text(self, update: Update) -> str:
        """Create a searchable text representation of an update."""
        return f"{update.title} {update.description} Provider: {update.provider} Product: {update.product_name}"
    
    def build_index(self, updates: List[Update]):
        """Build a FAISS index from a list of updates."""
        self.updates = updates
        texts = [self.create_update_text(update) for update in updates]
        embeddings = self.model.encode(texts)
        
        # Initialize FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings).astype('float32'))
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar updates using the query."""
        if not self.index:
            return []
            
        # Get query embedding and search
        query_embedding = self.model.encode([query])
        distances, indices = self.index.search(np.array(query_embedding).astype('float32'), k)
        
        # Format results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.updates):
                update = self.updates[idx]
                results.append({
                    'update': update,
                    'score': float(1 / (1 + distances[0][i]))  # Convert distance to similarity score
                })
        
        return results
