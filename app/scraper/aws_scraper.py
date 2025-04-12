"""AWS updates scraper module."""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from app.models import Update
from app import db

class AWSScraper:
    """Scraper for AWS updates RSS feed."""
    
    def __init__(self):
        self.feed_url = "https://aws.amazon.com/new/feed/"
    
    def clean_html(self, html_content):
        """Clean HTML content using BeautifulSoup."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    def parse_date(self, date_str):
        """Parse date string into datetime object."""
        try:
            return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                return None

    def extract_product(self, title, description):
        """Extract AWS product name from title or description."""
        # Common AWS service prefixes
        aws_prefixes = ['AWS', 'Amazon']
        
        # Try to find "AWS ServiceName" or "Amazon ServiceName" in title
        for prefix in aws_prefixes:
            pattern = fr'{prefix}\s+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)'
            match = re.search(pattern, title)
            if match:
                return f"{prefix} {match.group(1)}"
        
        # If not found in title, try description
        if description:
            for prefix in aws_prefixes:
                pattern = fr'{prefix}\s+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)'
                match = re.search(pattern, description)
                if match:
                    return f"{prefix} {match.group(1)}"
        
        return None

    def parse_entry(self, entry):
        """Parse a single RSS entry into an Update object."""
        # Extract basic fields
        title = entry.get('title', '').strip()
        link = entry.get('link', '').strip()
        description = self.clean_html(entry.get('description', ''))
        published_date = self.parse_date(entry.get('pubDate', ''))
        
        if not all([title, link, published_date]):
            return None
        
        # Extract product name
        product = self.extract_product(title, description)
        
        # Create Update object
        update = Update(
            title=title,
            link=link,
            description=description,
            published_date=published_date,
            provider='aws',
            product=product
        )
        
        return update

    def scrape(self):
        """Scrape AWS updates from RSS feed."""
        try:
            # Fetch RSS feed
            response = requests.get(self.feed_url)
            response.raise_for_status()
            
            # Parse XML with BeautifulSoup
            soup = BeautifulSoup(response.content, 'xml')
            entries = []
            
            # Extract entries
            for item in soup.find_all('item'):
                entry = {
                    'title': item.title.text if item.title else '',
                    'link': item.link.text if item.link else '',
                    'description': item.description.text if item.description else '',
                    'pubDate': item.pubDate.text if item.pubDate else None
                }
                entries.append(entry)
            
            # Process entries
            updates = []
            for entry in entries:
                update = self.parse_entry(entry)
                if update:
                    updates.append(update)
            
            return updates
            
        except Exception as e:
            print(f"Error scraping AWS updates: {str(e)}")
            return []
