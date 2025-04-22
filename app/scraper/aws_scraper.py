"""AWS updates scraper module."""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from app.models import Update
from app import db
from app.utils.update_processor import UpdateProcessor

class AWSScraper:
    """Scraper for AWS updates RSS feed."""
    
    def __init__(self):
        self.feed_url = "https://aws.amazon.com/new/feed/"
        self.processor = UpdateProcessor()
    
    def clean_html(self, html_content):
        """Clean HTML content using BeautifulSoup and truncate to reasonable length."""
        if not html_content:
            return ""
            
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'table', 'ul', 'ol', 'img']):
            element.decompose()
            
        # Get text with proper spacing
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common AWS boilerplate text
        boilerplate = [
            "Learn more about AWS",
            "For more information, visit",
            "To learn more, please visit",
            "For more information, see",
            "Please visit the documentation",
            "For more details, see",
            "To get started with",
            "You can learn more about",
            "For additional information",
            "For pricing details",
            "Visit the AWS",
            "Check out the documentation"
        ]
        
        for phrase in boilerplate:
            if phrase in text:
                text = text.split(phrase)[0].strip()
        
        # Limit to 3 sentences maximum
        sentences = text.split('. ')
        if len(sentences) > 3:
            text = '. '.join(sentences[:3]) + '.'
            
        # Remove trailing punctuation
        text = text.strip('.,!?;:')
        
        # Add ellipsis if truncated
        if len(sentences) > 3:
            text += '...'
            
        return text

    def parse_date(self, date_str):
        """Parse date string into datetime object."""
        if not date_str:
            return None
            
        print(f"Parsing date: {date_str}")
        
        # Remove GMT/UTC if present
        date_str = date_str.replace(' GMT', '').replace(' UTC', '')
        
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # With timezone
            '%a, %d %b %Y %H:%M:%S',      # Without timezone
            '%Y-%m-%dT%H:%M:%SZ'          # ISO format
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError as e:
                print(f"Failed format {fmt}: {str(e)}")
                continue
                
        print(f"Could not parse date: {date_str}")
        return None

    def parse_entry(self, entry):
        """Parse a single RSS entry into an Update object."""
        # Extract basic fields
        title = entry.get('title', '').strip()
        link = entry.get('link', '').strip()
        description = self.clean_html(entry.get('description', ''))
        published_date = self.parse_date(entry.get('pubDate', ''))
        
        print(f"\nProcessing entry:")
        print(f"Title: {title}")
        print(f"Link: {link}")
        print(f"Published: {published_date}")
        
        if not all([title, link, published_date]):
            print("Missing required fields!")
            if not title:
                print("- Missing title")
            if not link:
                print("- Missing link")
            if not published_date:
                print("- Missing published_date")
            return None
        
        # Process update metadata
        metadata = self.processor.process_aws_update({
            'title': title,
            'description': description
        })
        
        try:
            # Create Update object
            update = Update(
                title=title,
                url=link,
                description=description,
                published_date=published_date,
                provider='aws',
                product_name=metadata['product_name']
            )
            print("Successfully created Update object")
            return update
        except Exception as e:
            print(f"Error creating Update object: {str(e)}")
            return None

    def scrape(self):
        """Scrape AWS updates from RSS feed."""
        try:
            print("Fetching AWS RSS feed...")
            # Fetch RSS feed
            response = requests.get(self.feed_url)
            response.raise_for_status()
            print(f"Got response: {response.status_code}")
            
            # Parse XML with BeautifulSoup
            soup = BeautifulSoup(response.content, 'xml')
            print(f"Parsed XML response")
            
            entries = []
            
            # Extract entries
            items = soup.find_all('item')
            print(f"Found {len(items)} items in feed")
            
            # Debug first item
            if items:
                first_item = items[0]
                print("\nFirst item raw XML:")
                print(first_item.prettify())
            
            for item in items:
                entry = {
                    'title': item.title.text if item.title else '',
                    'link': item.link.text if item.link else '',
                    'description': item.description.text if item.description else '',
                    'pubDate': item.pubDate.text if item.pubDate else None
                }
                entries.append(entry)
            
            print(f"Extracted {len(entries)} entries")
            if entries:
                print("\nFirst entry data:")
                print(entries[0])
            
            # Process entries
            updates = []
            for entry in entries:
                update = self.parse_entry(entry)
                if update:
                    updates.append(update)
            
            print(f"Created {len(updates)} Update objects")
            return updates
            
        except Exception as e:
            print(f"Error scraping AWS updates: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
