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
from typing import List
import feedparser
from time import mktime
from app.models import Update

class AWSScraper:
    def __init__(self):
        self.feed_url = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"

    def scrape(self) -> List[Update]:
        try:
            print(f"Fetching AWS feed from {self.feed_url}")
            feed = feedparser.parse(self.feed_url)
            
            if hasattr(feed, 'status') and feed.status != 200:
                print(f"Error: AWS feed returned status {feed.status}")
                return []
                
            if not hasattr(feed, 'entries'):
                print("Error: AWS feed has no entries")
                return []
                
            print(f"Successfully fetched AWS feed with {len(feed.entries)} entries")
            
            updates = []
            for entry in feed.entries:
                try:
                    if not hasattr(entry, 'published_parsed'):
                        print(f"Warning: AWS entry missing published date: {entry.get('title', 'No title')}")
                        continue
                        
                    # Convert the time struct to datetime
                    published_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    description = entry.get('description', '')
                    if not description and hasattr(entry, 'summary'):
                        description = entry.summary
                    
                    update = Update(
                        provider='aws',
                        title=entry.get('title', 'No title'),
                        description=description,
                        url=entry.get('link', ''),
                        published_date=published_date
                    )
                    updates.append(update)
                except Exception as entry_error:
                    print(f"Error processing AWS entry: {entry_error}")
                    continue
            
            print(f"Successfully processed {len(updates)} AWS updates")
            return updates
            
        except Exception as e:
            print(f"Error fetching AWS RSS feed: {e}")
            return []
