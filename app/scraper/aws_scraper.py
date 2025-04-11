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

    def _extract_potential_service_name(self, title):
        """Extract potential service name from title by looking for AWS/Amazon prefix followed by capitalized words."""
        import re
        
        # Common AWS region prefixes to exclude
        region_prefixes = [
            r'AWS Europe',
            r'AWS Asia Pacific',
            r'AWS Middle East',
            r'AWS North America',
            r'AWS South America',
            r'AWS Africa',
            r'AWS US',
            r'AWS Canada',
        ]
        
        # Look for "AWS" or "Amazon" prefix followed by capitalized words
        patterns = [
            r'AWS\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)',  # Allow mixed case after first capital
            r'Amazon\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)'
        ]
        
        # First try to find the earliest match in the title
        earliest_match = None
        earliest_pos = len(title)
        
        for pattern in patterns:
            for match in re.finditer(pattern, title):
                # Skip if this matches a region prefix
                is_region = any(re.match(f"{prefix}\\b", match.group(0)) for prefix in region_prefixes)
                if not is_region:
                    pos = match.start()
                    if pos < earliest_pos:
                        earliest_pos = pos
                        earliest_match = match
                        prefix = "AWS" if pattern.startswith("AWS") else "Amazon"
        
        if earliest_match:
            # Get the words that follow
            service_name = earliest_match.group(1)
            # Only take words until we hit a word that doesn't start with capital
            words = []
            for word in service_name.split():
                if not word[0].isupper():
                    break
                words.append(word)
            if words:
                return f"{prefix} {' '.join(words)}"
        
        return None

    def extract_product_name(self, title):
        """Extract AWS product name by finding perfect matches with the services list."""
        import re
        services = self._get_services()
        
        # First try exact matches at the start of the title
        for service in services:
            # Create regex pattern with word boundaries
            pattern = r'^' + re.escape(service) + r'\b'
            if re.search(pattern, title):
                return service
            
            # Try without prefix if it starts with "Amazon" or "AWS"
            if service.startswith(("Amazon ", "AWS ")):
                short_name = service.split(" ", 1)[1]
                pattern = r'^(?:Amazon|AWS)\s+' + re.escape(short_name) + r'\b'
                if re.search(pattern, title):
                    return service

        # Then try exact matches anywhere in the title
        for service in services:
            # Create regex pattern with word boundaries
            pattern = r'\b' + re.escape(service) + r'\b'
            if re.search(pattern, title):
                return service
            
            # Try without prefix if it starts with "Amazon" or "AWS"
            if service.startswith(("Amazon ", "AWS ")):
                short_name = service.split(" ", 1)[1]
                pattern = r'\b' + re.escape(short_name) + r'\b'
                if re.search(pattern, title):
                    return service
        
        # If no match found in cache, try to extract potential service name from title
        return self._extract_potential_service_name(title)

    def clean_description(self, description, product_name=None):
        """Clean the HTML description and add AWS Product section."""
        # First convert HTML entities
        clean_text = description
        clean_text = clean_text.replace('&nbsp;', ' ')
        clean_text = clean_text.replace('&amp;', '&')
        clean_text = clean_text.replace('&lt;', '<')
        clean_text = clean_text.replace('&gt;', '>')
        clean_text = clean_text.replace('&quot;', '"')
        clean_text = clean_text.replace('&#39;', "'")
        clean_text = clean_text.replace('&#8217;', "'")
        clean_text = clean_text.replace('&#8220;', '"')
        clean_text = clean_text.replace('&#8221;', '"')
        clean_text = clean_text.replace('&#8211;', "-")
        clean_text = clean_text.replace('&#8230;', "...")
        
        # Remove HTML tags
        clean_text = re.sub(r'<a[^>]*>', '', clean_text)  # Remove opening <a> tags
        clean_text = re.sub(r'</a>', '', clean_text)      # Remove closing </a> tags
        clean_text = re.sub(r'<p[^>]*>', '', clean_text)  # Remove opening <p> tags
        clean_text = re.sub(r'</p>', '\n\n', clean_text)  # Replace closing </p> with newlines
        clean_text = re.sub(r'<br[^>]*>', '\n', clean_text)  # Replace <br> with newline
        clean_text = re.sub(r'<[^>]+>', '', clean_text)   # Remove any remaining tags
        
        # Fix common issues
        clean_text = re.sub(r'\s+', ' ', clean_text)      # Replace multiple spaces with single space
        clean_text = re.sub(r'\s*\.\s*\.\s*\.', '...', clean_text)  # Fix ellipsis
        clean_text = re.sub(r'\s*-\s*', '-', clean_text)  # Fix dashes
        clean_text = clean_text.strip()
        
        # Split description into parts by looking for the timestamp pattern
        timestamp_pattern = r'\n*Posted On: [A-Za-z]+ \d+, \d{4}'
        parts = re.split(timestamp_pattern, clean_text, maxsplit=1)
        
        if len(parts) == 2:
            main_text, timestamp = parts
            # Add AWS Product section before timestamp
            product_section = f"\n\nAWS Product:\n• {product_name if product_name else ''}"
            clean_text = f"{main_text.strip()}{product_section}\n\nPosted On:{timestamp.strip()}"
        else:
            # If no timestamp found, just append the product section
            clean_text = f"{clean_text}\n\nAWS Product:\n• {product_name if product_name else ''}"
        
        return clean_text

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
                    
                    # Clean description and add AWS Product section if available
                    clean_description = self.clean_description(entry.description, product_name)
                    
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
