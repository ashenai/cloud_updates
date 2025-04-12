"""Utility functions for cleaning updates."""
from app import db
from app.models import Update
from app.utils.clean_updates import clean_aws_updates, clean_azure_updates

def clean_all_updates(delete_old=False):
    """Clean both AWS and Azure updates."""
    # Clean Azure updates
    azure_updates = Update.query.filter_by(provider='azure').all()
    azure_removed = clean_azure_updates(azure_updates, delete_old=delete_old)
    
    # Clean AWS updates
    aws_updates = Update.query.filter_by(provider='aws').all()
    aws_removed = clean_aws_updates(aws_updates, delete_old=delete_old)
    
    return azure_removed + aws_removed

def clean_aws_duplicates(delete_old=False):
    """Clean AWS updates by removing duplicates."""
    updates = Update.query.filter_by(provider='aws').all()
    return clean_aws_updates(updates, delete_old=delete_old)

def clean_azure_duplicates(delete_old=False):
    """Clean Azure updates by removing duplicates."""
    updates = Update.query.filter_by(provider='azure').all()
    return clean_azure_updates(updates, delete_old=delete_old)
