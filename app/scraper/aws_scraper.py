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

class AWSScraper:
    def __init__(self):
        self.feed_url = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
        
        # Define update patterns
        self.update_patterns = [
            (r'\bpreview\b', 'Preview'),
            (r'now available|general availability|generally available|\bga\b', 'Generally Available'),
            (r'launch|introduce|announce|release', 'Features'),
            (r'retire|deprecate|end of life|end-of-life', 'Retirements'),
            (r'region|datacenter|data center|availability zone', 'Regions & Datacenters'),
            (r'price|pricing|cost', 'Pricing & Offerings'),
            (r'compliance|iso|hipaa|fedramp|soc', 'Compliance'),
            (r'security|encryption|protect', 'Security'),
            (r'sdk|api|cli|tool', 'SDK and Tools')
        ]

    def clean_description(self, description: str) -> str:
        """Clean HTML tags from description."""
        if not description:
            return ""
        # Parse HTML and get text
        soup = BeautifulSoup(description, 'html.parser')
        return soup.get_text().strip()

    def extract_categories(self, title: str) -> List[str]:
        """Extract AWS service categories from the update title."""
        categories = []
        
        # Common AWS service patterns
        patterns = [
            r'Amazon ([\w\s]+)',
            r'AWS ([\w\s]+)',
            r'Amazon Web Services ([\w\s]+)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, title)
            for match in matches:
                service = match.group(1).strip()
                if service and service not in categories:
                    categories.append(service)
        
        # Add the first word if no matches found (often the service name in AWS titles)
        if not categories and title:
            categories.append(title.split()[0])
        
        # Ensure we have at least one category
        if not categories:
            categories.append('General')
        
        return categories

    def determine_update_types(self, title: str, description: str) -> List[str]:
        """Determine the types of update based on title and description content."""
        update_types = []
        combined_text = f"{title} {description}".lower()
        
        # Check each pattern for matches
        for pattern, update_type in self.update_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                update_types.append(update_type)
        
        # Ensure we have at least one update type
        if not update_types:
            update_types.append('Features')  # Default to Features if no specific type is found
        
        return update_types

    def scrape(self) -> List[Update]:
        """Scrape AWS updates from RSS feed."""
        try:
            print(f"Fetching AWS feed from {self.feed_url}")
            feed = feedparser.parse(self.feed_url)
            
            if hasattr(feed, 'status') and feed.status != 200:
                print(f"Error: AWS feed returned status {feed.status}")
                return []
                
            if not hasattr(feed, 'entries'):
                print("Error: AWS feed has no entries")
                return []
                
            print(f"Found {len(feed.entries)} AWS updates")
            
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
                        print(f"Warning: AWS entry missing published date: {title}")
                        continue
                        
                    published_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    # Clean description
                    clean_description = self.clean_description(description)
                    
                    # Extract metadata
                    categories = self.extract_categories(title)
                    update_types = self.determine_update_types(title, clean_description)
                    
                    # Create update object
                    update = Update(
                        provider='aws',
                        title=title,
                        description=clean_description,
                        url=entry.get('link', ''),
                        published_date=published_date,
                        categories=categories,
                        update_types=update_types
                    )
                    updates.append(update)
                except Exception as entry_error:
                    print(f"Error processing AWS entry: {entry_error}")
                    continue
            
            print(f"Successfully processed {len(updates)} AWS updates")
            return updates
            
        except Exception as e:
            print(f"Error scraping AWS updates: {e}")
            return []
