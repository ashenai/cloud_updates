"""
Utility for analyzing and generating weekly themes from cloud updates.
"""
from datetime import datetime, timedelta
from collections import defaultdict
import re
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
import numpy as np
from app.models import Update, WeeklyTheme
from app import db

def get_week_start(date: datetime) -> datetime:
    """Get the start of the week (Monday) for a given date."""
    return date - timedelta(days=date.weekday())

def preprocess_text(text: str) -> str:
    """Clean and preprocess text for analysis."""
    # Remove special characters and convert to lowercase
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

class ThemeAnalyzer:
    """Class for analyzing and generating themes from cloud updates."""
    
    def __init__(self):
        """Initialize the theme analyzer."""
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def generate_themes(self, updates: List[Update], min_updates: int = 2) -> List[Dict]:
        """Generate themes from a list of updates."""
        if not updates:
            return []
        
        # Group updates by provider
        updates_by_provider = defaultdict(list)
        for update in updates:
            updates_by_provider[update.provider].append(update)
        
        # Process each provider separately
        all_themes = []
        for provider, provider_updates in updates_by_provider.items():
            themes = self._extract_themes(provider_updates, min_updates)
            all_themes.extend([
                {
                    'provider': provider,
                    'name': name,
                    'description': desc,
                    'score': score,
                    'update_count': count
                }
                for name, desc, score, count in themes
            ])
        
        return sorted(all_themes, key=lambda x: x['score'], reverse=True)
    
    def _extract_themes(self, updates: List[Update], min_updates: int = 2) -> List[Tuple[str, str, float, int]]:
        """Extract themes from a list of updates using TF-IDF and clustering."""
        if not updates:
            return []
        
        # Combine titles and descriptions for analysis
        texts = [f"{update.title} {update.description or ''}" for update in updates]
        preprocessed_texts = [preprocess_text(text) for text in texts]
        
        # Create TF-IDF matrix
        tfidf_matrix = self.vectorizer.fit_transform(preprocessed_texts)
        
        # Cluster updates
        clustering = DBSCAN(eps=0.5, min_samples=min_updates)
        clusters = clustering.fit_predict(tfidf_matrix.toarray())
        
        # Get important terms for each cluster
        themes = []
        for cluster_id in set(clusters):
            if cluster_id == -1:  # Skip noise
                continue
                
            # Get updates in this cluster
            cluster_indices = np.where(clusters == cluster_id)[0]
            cluster_updates = [updates[i] for i in cluster_indices]
            
            # Get common products/categories
            products = defaultdict(int)
            for update in cluster_updates:
                if update.product:
                    products[update.product] += 1
            
            # Get important terms
            cluster_texts = [preprocessed_texts[i] for i in cluster_indices]
            cluster_matrix = self.vectorizer.transform(cluster_texts)
            importance_scores = np.asarray(cluster_matrix.mean(axis=0)).flatten()
            important_terms = [
                term for term, score in 
                sorted(zip(self.vectorizer.get_feature_names_out(), importance_scores), 
                      key=lambda x: x[1], reverse=True)[:5]
            ]
            
            # Create theme name and description
            theme_name = ' '.join(important_terms[:2]).title()
            description = (
                f"Theme covering {len(cluster_updates)} updates related to {', '.join(important_terms)}. "
                f"Main products: {', '.join(sorted(products, key=products.get, reverse=True)[:3])}"
            )
            
            # Calculate relevance score based on number of updates and their recency
            max_age = max(datetime.utcnow() - update.published_date for update in cluster_updates).days
            age_factor = 1 / (1 + max_age/7)  # Decay with age
            size_factor = min(len(cluster_updates) / len(updates), 1)  # Proportion of total updates
            relevance_score = (age_factor + size_factor) / 2
            
            themes.append((
                theme_name,
                description,
                relevance_score,
                len(cluster_updates)
            ))
        
        # Sort by relevance score
        return sorted(themes, key=lambda x: x[2], reverse=True)

def generate_weekly_themes():
    """Generate weekly themes for both AWS and Azure updates."""
    # Get current week's start
    week_start = get_week_start(datetime.utcnow())
    
    # Process each provider
    for provider in ['aws', 'azure']:
        # Get this week's updates
        updates = Update.query.filter(
            Update.provider == provider,
            Update.published_date >= week_start
        ).all()
        
        # Delete existing themes for this week/provider
        WeeklyTheme.query.filter_by(
            week_start=week_start,
            provider=provider
        ).delete()
        
        # Extract new themes
        analyzer = ThemeAnalyzer()
        themes = analyzer.generate_themes(updates)
        
        # Save themes
        for theme in themes[:4]:  # Top 4 themes
            theme_obj = WeeklyTheme(
                week_start=week_start,
                provider=theme['provider'],
                theme_name=theme['name'],
                description=theme['description'],
                relevance_score=theme['score'],
                update_count=theme['update_count']
            )
            db.session.add(theme_obj)
    
    db.session.commit()
