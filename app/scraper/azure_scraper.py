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

from datetime import datetime
from typing import List, Tuple
import feedparser
from bs4 import BeautifulSoup
import re
from app.models import Update
from time import mktime

class AzureScraper:
    def __init__(self):
        self.feed_url = "https://www.microsoft.com/releasecommunications/api/v2/azure/rss"
        
        # Define known update types that appear in category tags
        self.update_type_categories = {
            'Compliance',
            'Features',
            'Gallery',
            'Management',
            'Microsoft Build',
            'Microsoft Ignite',
            'Microsoft Connect',
            'Microsoft Inspire',
            'MicrosoftBuild',
            'Open Source',
            'Operating System',
            'Pricing & Offerings',
            'Regions & Datacenters',
            'Retirements',
            'SDK and Tools',
            'Security',
            'Services'
        }

    def clean_description(self, description: str) -> str:
        """Clean HTML tags from description."""
        if not description:
            return ""
        # Parse HTML and get text
        soup = BeautifulSoup(description, 'html.parser')
        return soup.get_text().strip()

    def extract_metadata(self, entry) -> Tuple[List[str], List[str]]:
        """Extract categories and update types from entry metadata."""
        categories = []
        update_types = []
        
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                tag_term = tag.get('term', '').strip()
                # Skip empty tags
                if not tag_term:
                    continue
                # If the tag is a known update type, add it to update types
                if tag_term in self.update_type_categories:
                    update_types.append(tag_term)
                else:
                    # Otherwise, it's a category
                    categories.append(tag_term)
        
        # Ensure we have at least one category and update type
        if not categories:
            categories = ['General']
        if not update_types:
            update_types = ['Features']
        
        return categories, update_types

    def scrape(self) -> List[Update]:
        """Scrape Azure updates from RSS feed."""
        try:
            print(f"Fetching Azure feed from {self.feed_url}")
            feed = feedparser.parse(self.feed_url)
            
            if hasattr(feed, 'status') and feed.status != 200:
                print(f"Error: Azure feed returned status {feed.status}")
                return []
                
            if not hasattr(feed, 'entries'):
                print("Error: Azure feed has no entries")
                return []
                
            print(f"Found {len(feed.entries)} Azure updates")
            
            updates = []
            for entry in feed.entries:
                try:
                    # Get description from content or summary
                    description = ''
                    if hasattr(entry, 'content'):
                        description = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        description = entry.summary
                    
                    title = entry.get('title', 'No title')
                    
                    # Convert the time struct to datetime
                    if not hasattr(entry, 'published_parsed'):
                        print(f"Warning: Azure entry missing published date: {title}")
                        continue
                        
                    published_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    # Extract metadata
                    categories, update_types = self.extract_metadata(entry)
                    
                    # Create update object
                    update = Update(
                        provider='azure',
                        title=title,
                        description=self.clean_description(description),
                        url=entry.get('link', ''),
                        published_date=published_date,
                        categories=categories,
                        update_types=update_types
                    )
                    updates.append(update)
                except Exception as entry_error:
                    print(f"Error processing Azure entry: {entry_error}")
                    continue
            
            print(f"Successfully processed {len(updates)} Azure updates")
            return updates
            
        except Exception as e:
            print(f"Error scraping Azure updates: {e}")
            return []
