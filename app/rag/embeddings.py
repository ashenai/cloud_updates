"""
Enhanced search implementation using scikit-learn with advanced text processing
and semantic matching capabilities.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
import numpy as np
from datetime import datetime, timezone
import re
from typing import List, Dict, Set, Tuple
from app.models import Update

class UpdateSearch:
    def __init__(self):
        # Initialize TF-IDF vectorizer with optimized parameters
        self.vectorizer = TfidfVectorizer(
            max_features=10000,  # Increased vocabulary size
            stop_words='english',
            ngram_range=(1, 3),  # Include up to trigrams
            min_df=2,  # Terms must appear in at least 2 documents
            max_df=0.9,  # Ignore terms that appear in >90% of docs
            norm='l2',  # L2 normalization
            use_idf=True,
            smooth_idf=True,
            sublinear_tf=True  # Apply sublinear scaling to term frequencies
        )
        self.updates = []
        self.tfidf_matrix = None
        self.product_keywords = set()
        
    def preprocess_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:  # Handle None or empty string
            return ""
            
        # Convert to lowercase
        text = str(text).lower()
        
        # Replace special characters with space
        text = re.sub(r'[^a-z0-9\s-]', ' ', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Add spaces around numbers to treat them as separate tokens
        text = re.sub(r'(\d+)', r' \1 ', text)
        
        return text.strip()
    
    def extract_keywords(self, text: str) -> Set[str]:
        """Extract important keywords from text."""
        if not text:  # Handle None or empty string
            return set()
            
        # Common cloud computing terms
        cloud_terms = {
            'machine learning', 'ai', 'artificial intelligence', 'ml',
            'database', 'storage', 'compute', 'serverless', 'container',
            'kubernetes', 'docker', 'security', 'monitoring', 'analytics',
            'data', 'network', 'api', 'service', 'cloud', 'virtual',
            'instance', 'server', 'cluster', 'pipeline', 'deployment',
            'infrastructure', 'platform', 'integration', 'automation',
            'backup', 'recovery', 'scaling', 'performance', 'optimization'
        }
        
        # Extract words that match cloud terms
        text_lower = str(text).lower()
        found_terms = set()
        
        for term in cloud_terms:
            if term in text_lower:
                found_terms.add(term)
        
        # Add product names
        for product in self.product_keywords:
            if product and product.lower() in text_lower:
                found_terms.add(product.lower())
        
        return found_terms
    
    def create_update_text(self, update: Update) -> Tuple[str, Set[str]]:
        """Create searchable text and extract keywords from an update."""
        # Build rich text representation with null checks
        title = self.preprocess_text(update.title or '')
        description = self.preprocess_text(update.description or '')
        provider = (update.provider or '').lower()
        product = self.preprocess_text(update.product_name or '')
        
        # Create weighted text (repeat important fields)
        text_parts = []
        
        if title:
            text_parts.extend([title] * 3)  # Title is most important
        
        if description:
            text_parts.append(description)
        
        if provider:
            text_parts.extend([f"provider {provider}"] * 2)
        
        if product:
            text_parts.extend([f"product {product}"] * 2)
        
        # Extract keywords with null checks
        keywords = set()
        if title:
            keywords.update(self.extract_keywords(title))
        if description:
            keywords.update(self.extract_keywords(description))
        if provider:
            keywords.add(provider)
        if product:
            keywords.add(product)
        
        # Add keywords explicitly to the text
        if keywords:
            text_parts.append(" ".join(keywords))
        
        # Return empty string if no valid text parts
        final_text = " ".join(text_parts).strip()
        if not final_text:
            final_text = "empty update"  # Fallback for completely empty updates
        
        return final_text, keywords
    
    def detect_provider_filter(self, query: str) -> str:
        """Detect provider filter in query with improved accuracy."""
        if not query:  # Handle None or empty string
            return None
            
        query_lower = str(query).lower()
        
        # AWS patterns
        aws_patterns = {'aws', 'amazon', 'amazon web services'}
        for pattern in aws_patterns:
            if pattern in query_lower:
                return 'aws'
        
        # Azure patterns
        azure_patterns = {'azure', 'microsoft azure', 'microsoft cloud'}
        for pattern in azure_patterns:
            if pattern in query_lower:
                return 'azure'
        
        return None
    
    def build_index(self, updates: List[Update]):
        """Build search index from updates."""
        if not updates:  # Handle empty updates list
            self.updates = []
            self.tfidf_matrix = None
            self.product_keywords = set()
            return
            
        self.updates = updates
        
        # Build product keyword set with null check
        self.product_keywords = {update.product_name for update in updates if update.product_name}
        
        # Create document texts and extract keywords
        texts = []
        for update in updates:
            text, _ = self.create_update_text(update)
            texts.append(text)
        
        # Fit and transform documents
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        
        # Normalize the matrix for better similarity computation
        self.tfidf_matrix = normalize(self.tfidf_matrix, norm='l2', axis=1)
    
    def compute_relevance_score(self, base_score: float, query_keywords: Set[str], 
                              update_keywords: Set[str], provider_filter: str, 
                              update: Update) -> float:
        """Compute final relevance score with multiple factors."""
        score = base_score
        
        # Keyword match bonus
        matching_keywords = query_keywords & update_keywords
        keyword_bonus = len(matching_keywords) * 0.1
        score += keyword_bonus
        
        # Provider boost/penalty
        if provider_filter and update.provider:
            if update.provider == provider_filter:
                score *= 2.0  # Double score for matching provider
            else:
                score *= 0.2  # Reduce score for non-matching provider
        
        # Recent content bonus (within last 30 days)
        if update.published_date:
            # Both times are in UTC - database stores UTC and we'll use UTC for comparison
            now = datetime.utcnow()
            days_old = (now - update.published_date).days
            if days_old <= 30:
                score *= 1.2  # 20% boost for recent content
        
        # Title match bonus
        if update.title and query_keywords:
            if any(keyword.lower() in update.title.lower() for keyword in query_keywords):
                score *= 1.5  # 50% boost for title matches
        
        return score
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar updates with improved ranking."""
        if not self.updates or self.tfidf_matrix is None:
            return []
        
        # Handle empty query
        if not query:
            return []
            
        # Preprocess query
        query = self.preprocess_text(query)
        query_keywords = self.extract_keywords(query)
        
        # Detect provider filter
        provider_filter = self.detect_provider_filter(query)
        
        # Transform query
        query_vector = self.vectorizer.transform([query])
        query_vector = normalize(query_vector, norm='l2', axis=1)
        
        # Compute base similarities
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # Compute final scores with null checks
        scored_results = []
        for idx, base_score in enumerate(similarities):
            if base_score > 0.01:  # Minimum similarity threshold
                update = self.updates[idx]
                _, update_keywords = self.create_update_text(update)
                
                # Compute final relevance score
                final_score = self.compute_relevance_score(
                    base_score, query_keywords, update_keywords,
                    provider_filter, update
                )
                
                scored_results.append((final_score, idx))
        
        # Sort by final score
        scored_results.sort(reverse=True)
        
        # Return top k results
        results = []
        for score, idx in scored_results[:k]:
            if score > 0.01:  # Final minimum threshold
                results.append({
                    'update': self.updates[idx],
                    'score': float(score)
                })
        
        return results
