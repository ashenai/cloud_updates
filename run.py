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

from app import create_app, db
import threading
import time
import schedule
from app.scraper.aws_scraper import AWSScraper
from app.scraper.azure_scraper import AzureScraper
from app.models import Update, WeeklyInsight
from datetime import datetime, timedelta

# Create the Flask app instance
app = create_app()

def generate_weekly_insights():
    """Generate weekly insights from updates."""
    with app.app_context():
        # Get updates from the last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Count updates by provider
        aws_count = Update.query.filter(
            Update.provider == 'aws',
            Update.published_date >= week_ago
        ).count()
        
        azure_count = Update.query.filter(
            Update.provider == 'azure',
            Update.published_date >= week_ago
        ).count()
        
        # Create weekly insight
        insight = WeeklyInsight(
            week_start=week_ago,
            week_end=datetime.utcnow(),
            aws_updates=aws_count,
            azure_updates=azure_count,
            summary=f"This week, AWS had {aws_count} updates and Azure had {azure_count} updates. " + \
                   f"{'AWS' if aws_count > azure_count else 'Azure'} was more active with " + \
                   f"{'more' if abs(aws_count - azure_count) > 0 else 'the same number of'} updates."
        )
        
        db.session.add(insight)
        db.session.commit()

def scrape_updates():
    with app.app_context():
        print("Fetching updates from AWS and Azure...")
        aws_scraper = AWSScraper()
        azure_scraper = AzureScraper()
        
        aws_updates = aws_scraper.scrape()
        azure_updates = azure_scraper.scrape()
        
        print(f"Found {len(aws_updates)} AWS updates and {len(azure_updates)} Azure updates")
        
        # Save updates to database
        new_updates = 0
        for update in aws_updates + azure_updates:
            try:
                db.session.add(update)
                db.session.commit()
                new_updates += 1
            except Exception as e:
                # Rollback the failed transaction
                db.session.rollback()
                if 'unique_update' in str(e):
                    # Skip duplicates silently
                    continue
                else:
                    # Log other errors
                    print(f"Error saving update: {e}")
        
        print(f"Added {new_updates} new updates to database")
        
        # Generate weekly insights after scraping
        generate_weekly_insights()

def run_scheduler():
    # Schedule the scraping job to run daily at 9 AM
    schedule.every().day.at("09:00").do(scrape_updates)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Run the Flask application
    app.run(debug=True)
