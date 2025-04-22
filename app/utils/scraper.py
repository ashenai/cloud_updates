"""Utility functions for scraping updates."""
from app.scraper.aws_scraper import AWSScraper
from app.scraper.azure_scraper import AzureScraper
from app import db
from app.models import Update
from sqlalchemy.exc import IntegrityError
from app.scraper.aws_services import AWSServicesFetcher

def scrape_aws_updates():
    """Scrape AWS updates."""
    print("\nStarting AWS updates scrape...")
    
    # First, refresh the AWS services cache
    try:
        print("Refreshing AWS services cache...")
        aws_services_fetcher = AWSServicesFetcher()
        services = aws_services_fetcher.get_services(refresh=True)
        print(f"AWS services cache refreshed. Found {len(services)} services.")
    except Exception as e:
        print(f"Warning: Failed to refresh AWS services cache: {str(e)}")
        print("Continuing with existing cache...")
    
    # Now scrape updates
    scraper = AWSScraper()
    updates = scraper.scrape()
    print(f"Got {len(updates)} AWS updates from scraper")
    count = 0
    
    # Save updates to database
    for update in updates:
        try:
            existing = db.session.query(db.exists().where(
                db.and_(
                    Update.provider == update.provider,
                    Update.title == update.title,
                    Update.published_date == update.published_date
                )
            )).scalar()
            
            if not existing:
                print(f"Adding new AWS update: {update.title}")
                db.session.add(update)
                count += 1
            else:
                print(f"Skipping existing AWS update: {update.title}")
        except IntegrityError as e:
            print(f"IntegrityError for AWS update: {update.title}")
            print(str(e))
            db.session.rollback()
            continue
        except Exception as e:
            print(f"Error processing AWS update: {update.title}")
            print(str(e))
            db.session.rollback()
            continue
    
    db.session.commit()
    print(f"Added {count} new AWS updates")
    return count

def scrape_azure_updates():
    """Scrape Azure updates."""
    print("\nStarting Azure updates scrape...")
    scraper = AzureScraper()
    updates = scraper.scrape()
    print(f"Got {len(updates)} Azure updates from scraper")
    count = 0
    
    # Save updates to database
    for update in updates:
        try:
            existing = db.session.query(db.exists().where(
                db.and_(
                    Update.provider == update.provider,
                    Update.title == update.title,
                    Update.published_date == update.published_date
                )
            )).scalar()
            
            if not existing:
                print(f"Adding new Azure update: {update.title}")
                db.session.add(update)
                count += 1
            else:
                print(f"Skipping existing Azure update: {update.title}")
        except IntegrityError as e:
            print(f"IntegrityError for Azure update: {update.title}")
            print(str(e))
            db.session.rollback()
            continue
        except Exception as e:
            print(f"Error processing Azure update: {update.title}")
            print(str(e))
            db.session.rollback()
            continue
    
    db.session.commit()
    print(f"Added {count} new Azure updates")
    return count
