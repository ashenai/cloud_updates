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
        self.feed_url = "https://www.microsoft.com/releasecommunications/api/v2/azure/rss"  # Official Azure RSS feed
    
    def get_update_date(self, entry_dict):
        """Get the most recent update date from entry."""
        # Try to get the a10:updated date first
        updated = entry_dict.get('updated')
        published = entry_dict.get('published')
        
        print(f"Parsing dates - Updated: {updated}, Published: {published}")
        
        # Remove GMT/UTC if present
        if updated:
            updated = updated.replace(' GMT', '').replace(' UTC', '')
        if published:
            published = published.replace(' GMT', '').replace(' UTC', '')
        
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # With timezone
            '%a, %d %b %Y %H:%M:%S',      # Without timezone
            '%Y-%m-%dT%H:%M:%SZ'          # ISO format
        ]
        
        # Try updated date first
        if updated:
            for fmt in formats:
                try:
                    return datetime.strptime(updated, fmt)
                except ValueError:
                    continue
        
        # Fall back to published date
        if published:
            for fmt in formats:
                try:
                    return datetime.strptime(published, fmt)
                except ValueError:
                    continue
        
        print("Could not parse any dates")
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
        
        print(f"\nProcessing Azure entry:")
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
        
        try:
            # Create Update object
            update = Update(
                title=title,
                url=link,
                description=description,
                published_date=published_date,
                provider='azure',
                categories=entry.get('categories', [])
            )
            print("Successfully created Azure Update object")
            return update
        except Exception as e:
            print(f"Error creating Azure Update object: {str(e)}")
            return None

    def scrape(self):
        """Scrape Azure updates from RSS feed."""
        try:
            print("Fetching Azure RSS feed...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.feed_url, headers=headers)
            response.raise_for_status()
            print(f"Got response: {response.status_code}")
            print("\nResponse content type:", response.headers.get('content-type', ''))
            
            # Parse XML with BeautifulSoup
            soup = BeautifulSoup(response.content, 'xml')
            print(f"\nParsed XML response")
            
            # Find the channel element
            channel = soup.find('channel')
            if not channel:
                print("No channel element found")
                return []
                
            # Extract entries from items
            items = channel.find_all('item')
            print(f"\nFound {len(items)} items in feed")
            
            if items:
                print("\nFirst item structure:")
                print(items[0].prettify())
            
            entries = []
            for item in items:
                entry = {
                    'title': item.title.text if item.title else '',
                    'link': item.link.text if item.link else '',
                    'description': item.description.text if item.description else '',
                    'published': item.pubDate.text if item.pubDate else None,
                    'updated': item.find('updated').text if item.find('updated') else None,
                    'categories': [cat.text for cat in item.find_all('category')] if item.find('category') else []
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
            print(f"Error scraping Azure updates: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
