"""
Production configuration settings for the cloud_updates application.
"""
import os
from datetime import timedelta

class Config:
    # Base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'cloud_updates.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    
   # Application settings
    UPDATES_PER_PAGE = 20  # Number of updates to show per page
    MAX_SEARCH_RESULTS = 100  # Maximum number of search results to return
    UPDATE_RETENTION_DAYS = 90  # Number of days to keep updates before cleaning

    
    # Production settings
    DEBUG = False
    TESTING = False
    SSL_REDIRECT = True
