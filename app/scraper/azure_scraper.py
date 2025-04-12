"""
Copyright 2025 Aavind K Shenai

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

DISCLAIMER:
This code was generated using artificial intelligence. While efforts have been made
to ensure its accuracy and functionality, users should:
1. Review and test the code thoroughly before deployment
2. Be aware that AI-generated code may contain unexpected behaviors
3. Use this code at their own risk
4. Not rely on this code for critical systems without proper validation
"""

"""Azure updates scraper module."""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from app.models import Update
from app import db

class AzureScraper:
    """Scraper for Azure updates RSS feed."""
    
    def __init__(self):
        self.feed_url = "https://azurecomcdn.azureedge.net/en-us/updates/feed/"
    
    def get_update_date(self, entry_dict):
        """Get the most recent update date from entry."""
        # Try to get the a10:updated date first
        updated = entry_dict.get('updated')
        if updated:
            try:
                return datetime.strptime(updated, '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                pass
        
        # Fall back to published date
        published = entry_dict.get('published')
        if published:
            try:
                return datetime.strptime(published, '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                pass
        
        return None

    def clean_html(self, html_content):
        """Clean HTML content using BeautifulSoup."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    def parse_entry(self, entry):
        """Parse a single RSS entry into an Update object."""
        # Extract basic fields
        title = entry.get('title', '').strip()
        link = entry.get('link', '').strip()
        description = self.clean_html(entry.get('description', ''))
        published_date = self.get_update_date(entry)
        
        if not all([title, link, published_date]):
            return None
        
        # Create Update object
        update = Update(
            title=title,
            link=link,
            description=description,
            published_date=published_date,
            provider='azure'
        )
        
        return update

    def scrape(self):
        """Scrape Azure updates from RSS feed."""
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
                    'published': item.pubDate.text if item.pubDate else None,
                    'updated': item.find('updated').text if item.find('updated') else None
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
            print(f"Error scraping Azure updates: {str(e)}")
            return []
