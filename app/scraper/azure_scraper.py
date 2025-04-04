from datetime import datetime
from typing import List
import feedparser
from time import mktime
from app.models import Update

class AzureScraper:
    def __init__(self):
        self.feed_url = "https://www.microsoft.com/releasecommunications/api/v2/azure/rss"

    def scrape(self) -> List[Update]:
        try:
            print(f"Fetching Azure feed from {self.feed_url}")
            feed = feedparser.parse(self.feed_url)
            
            if hasattr(feed, 'status') and feed.status != 200:
                print(f"Error: Azure feed returned status {feed.status}")
                return []
                
            if not hasattr(feed, 'entries'):
                print("Error: Azure feed has no entries")
                return []
                
            print(f"Successfully fetched Azure feed with {len(feed.entries)} entries")
            
            updates = []
            for entry in feed.entries:
                try:
                    if not hasattr(entry, 'published_parsed'):
                        print(f"Warning: Azure entry missing published date: {entry.get('title', 'No title')}")
                        continue
                        
                    # Convert the time struct to datetime
                    published_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    description = entry.get('summary', '')  # Azure RSS uses 'summary'
                    if not description and hasattr(entry, 'description'):
                        description = entry.description
                    
                    update = Update(
                        provider='azure',
                        title=entry.get('title', 'No title'),
                        description=description,
                        url=entry.get('link', ''),
                        published_date=published_date
                    )
                    updates.append(update)
                except Exception as entry_error:
                    print(f"Error processing Azure entry: {entry_error}")
                    continue
            
            print(f"Successfully processed {len(updates)} Azure updates")
            return updates
            
        except Exception as e:
            print(f"Error fetching Azure RSS feed: {e}")
            return []
