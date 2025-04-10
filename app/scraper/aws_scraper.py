"""
AWS Updates Scraper
"""

import feedparser
from datetime import datetime
import re
from email.utils import parsedate_to_datetime
import sys
import json
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from aws_services import AWSServicesFetcher

# Set stdout to use UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

class AWSScraper:
    def __init__(self):
        self.rss_url = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
        self._services_fetcher = AWSServicesFetcher()
        self._services = None

    def _get_services(self):
        """Get or load AWS services list."""
        if self._services is None:
            self._services = self._services_fetcher.get_services()
        return self._services

    def _clean_word(self, word):
        """Clean a word by removing punctuation and converting to lowercase."""
        return ''.join(c.lower() for c in word if c.isalnum())

    def _is_word_match(self, word, text):
        """Check if word appears as a complete word in text."""
        # Split into words and clean each word
        word_parts = [self._clean_word(w) for w in word.split()]
        text_parts = [self._clean_word(w) for w in text.split()]
        
        # For multi-word phrases, check if all words appear in sequence
        if len(word_parts) > 1:
            # Try to find the sequence starting at each word
            for i in range(len(text_parts)):
                if text_parts[i] == word_parts[0]:
                    # Check if remaining words follow in sequence
                    match = True
                    for j in range(1, len(word_parts)):
                        if i + j >= len(text_parts) or text_parts[i + j] != word_parts[j]:
                            match = False
                            break
                    if match:
                        print(f"Found sequence match: {word}")
                        return True
            return False
        
        # For single words, check if they appear as complete words
        word = word_parts[0]
        text = ' '.join(text_parts)
        text = f" {text} "
        return f" {word} " in text

    def extract_product_name(self, title):
        """
        Extract AWS product name from update title by:
        1. Try exact matches with full service names
        2. Try matches with base names (without AWS/Amazon prefix)
        """
        print(f"\nProcessing title: {title}")
        
        # Get services list from cache/docs
        services = self._get_services()
        
        # Sort services by length (descending) to prioritize longer matches
        services = sorted(services, key=len, reverse=True)
        
        # First try exact matches with full service names
        print("\nTrying exact matches:")
        matches = []
        for service in services:
            if self._is_word_match(service, title):
                matches.append(service)
                print(f"Found exact match: {service}")
        
        if matches:
            # Return the longest match
            longest_match = max(matches, key=len)
            print(f"Selected longest match: {longest_match}")
            return longest_match
        
        # Then try matches with base names (without AWS/Amazon prefix)
        print("\nTrying base name matches:")
        matches = []
        for service in services:
            base_name = service.replace('AWS ', '').replace('Amazon ', '')
            if len(base_name) <= 3:  # Skip short names to avoid false matches
                continue
                
            if self._is_word_match(base_name, title):
                matches.append(service)
                print(f"Found base name match: {service}")
        
        if matches:
            # Return the longest match
            longest_match = max(matches, key=len)
            print(f"Selected longest match: {longest_match}")
            return longest_match
        
        print("No product name found")
        return None

    def clean_description(self, description):
        """Clean the HTML description."""
        # For now, just return the raw description
        return description

    def scrape(self):
        """Scrape AWS updates from RSS feed."""
        try:
            feed = feedparser.parse(self.rss_url)
            if not feed.entries:
                print("No AWS entries found in feed")
                return []
                
            updates = []
            categories = []  # AWS doesn't provide categories in RSS
            
            for entry in feed.entries:
                try:
                    # Extract product name
                    product_name = self.extract_product_name(entry.title)
                    
                    # Skip entries without dates
                    if not entry.get('published'):
                        print(f"Warning: AWS entry missing published date: {entry.title}")
                        continue
                        
                    # Parse date using email.utils for RFC822 format
                    published_date = parsedate_to_datetime(entry.published)
                    
                    # Clean description
                    clean_description = self.clean_description(entry.description)
                    
                    # Create update object
                    update = {
                        'provider': 'aws',
                        'title': entry.title,
                        'description': clean_description,
                        'url': entry.get('link', ''),
                        'published_date': published_date,
                        'categories': categories,
                        'product_name': product_name,
                        'update_types': []  # AWS doesn't have explicit update types
                    }
                    updates.append(update)
                except Exception as entry_error:
                    print(f"Error processing AWS entry: {entry_error}")
                    continue
            
            print(f"\nSuccessfully processed {len(updates)} AWS updates")
            return updates
            
        except Exception as e:
            print(f"Error scraping AWS updates: {e}")
            return []

    def test_title(self):
        """Test method to check product extraction"""
        test_titles = [
            "Announcing pgvector 0.8.0 support in Aurora PostgreSQL",
            "Cost Optimization Hub supports DynamoDB and MemoryDB reservation recommendations",
            "New Guidance in the Well-Architected Tool"
        ]
        
        for title in test_titles:
            print(f"\nTesting title: {title}")
            product = self.extract_product_name(title)
            print(f"Found product: {product}")
        
        return product

if __name__ == "__main__":
    scraper = AWSScraper()
    scraper.test_title()
