"""
Utilities to clean and deduplicate AWS and Azure updates.
"""
from typing import List
from app.models import Update
from sqlalchemy import and_
from app import db
from datetime import datetime, timedelta

def clean_azure_updates(updates: List[Update], delete_old: bool = False) -> int:
    """
    Clean Azure updates by:
    1. Removing duplicates based on title and published date
    2. Optionally removing old updates (older than 90 days)
    3. Removing updates with missing critical fields
    
    Returns the number of updates removed.
    """
    initial_count = len(updates)
    removed = 0
    
    try:
        # Get existing updates from database for deduplication
        existing_updates = Update.query.filter_by(provider='azure').all()
        existing_map = {(u.title, u.published_date): u for u in existing_updates}
        
        # Filter out duplicates and invalid updates
        valid_updates = []
        for update in updates:
            # Skip updates with missing critical fields
            if not update.title or not update.published_date:
                removed += 1
                continue
                
            # Skip if this exact update already exists
            key = (update.title, update.published_date)
            if key in existing_map:
                removed += 1
                continue
                
            valid_updates.append(update)
        
        # Optionally remove old updates
        if delete_old:
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            old_updates = Update.query.filter(
                and_(
                    Update.provider == 'azure',
                    Update.published_date < cutoff_date
                )
            ).all()
            
            for update in old_updates:
                db.session.delete(update)
                removed += 1
        
        # Add valid updates to database
        for update in valid_updates:
            db.session.add(update)
        
        # Commit changes
        db.session.commit()
        
        print(f"Azure updates cleaning complete:")
        print(f"- Initial count: {initial_count}")
        print(f"- Updates removed: {removed}")
        print(f"- New updates added: {len(valid_updates)}")
        
        return removed
        
    except Exception as e:
        print(f"Error cleaning Azure updates: {e}")
        db.session.rollback()
        return 0

def clean_aws_updates(updates: List[Update], delete_old: bool = False) -> int:
    """
    Clean AWS updates by:
    1. Removing duplicates based on title and published date
    2. Optionally removing old updates (older than 90 days)
    3. Removing updates with missing critical fields
    
    Returns the number of updates removed.
    """
    initial_count = len(updates)
    removed = 0
    
    try:
        # Get existing updates from database for deduplication
        existing_updates = Update.query.filter_by(provider='aws').all()
        existing_map = {(u.title, u.published_date): u for u in existing_updates}
        
        # Filter out duplicates and invalid updates
        valid_updates = []
        for update in updates:
            # Skip updates with missing critical fields
            if not update.title or not update.published_date:
                removed += 1
                continue
                
            # Skip if this exact update already exists
            key = (update.title, update.published_date)
            if key in existing_map:
                removed += 1
                continue
                
            valid_updates.append(update)
        
        # Optionally remove old updates
        if delete_old:
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            old_updates = Update.query.filter(
                and_(
                    Update.provider == 'aws',
                    Update.published_date < cutoff_date
                )
            ).all()
            
            for update in old_updates:
                db.session.delete(update)
                removed += 1
        
        # Add valid updates to database
        for update in valid_updates:
            db.session.add(update)
        
        # Commit changes
        db.session.commit()
        
        print(f"AWS updates cleaning complete:")
        print(f"- Initial count: {initial_count}")
        print(f"- Updates removed: {removed}")
        print(f"- New updates added: {len(valid_updates)}")
        
        return removed
        
    except Exception as e:
        print(f"Error cleaning AWS updates: {e}")
        db.session.rollback()
        return 0
