"""Playwright test configuration."""
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
import os
import sys
import json
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.models import db, Update, WeeklyInsight, WeeklyTheme

def populate_test_data(db):
    """Populate database with test data from cloud_updates.json."""
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cloud_updates.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Process each table from the backup
    for table in data['objects']:
        if table['name'] == 'update':
            for row in table['rows']:
                if not isinstance(row, list) or len(row) < 12:  # Skip malformed rows
                    continue
                update = Update(
                    id=row[0],
                    provider=row[1],
                    title=row[2],
                    description=row[3],
                    url=row[4],
                    published_date=datetime.fromisoformat(row[5]) if row[5] else None,
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    categories=json.loads(row[7]) if row[7] else [],
                    update_types=json.loads(row[8]) if row[8] else [],
                    product_name=row[9],
                    status=json.loads(row[10]) if row[10] else [],
                    product_names=json.loads(row[11]) if row[11] else []
                )
                db.session.add(update)
        
        elif table['name'] == 'weekly_insights':  # Using weekly_insights instead of weekly_insight
            for row in table['rows']:
                if not isinstance(row, list) or len(row) < 7:  # Skip malformed rows
                    continue
                insight = WeeklyInsight(
                    id=row[0],
                    week_start=datetime.fromisoformat(row[1]) if row[1] else None,
                    week_end=datetime.fromisoformat(row[2]) if row[2] else None,
                    aws_updates=row[3],
                    azure_updates=row[4],
                    aws_top_products=row[5],
                    azure_top_categories=row[6]
                )
                db.session.add(insight)
        
        elif table['name'] == 'weekly_theme':
            for row in table['rows']:
                if not isinstance(row, list) or len(row) < 7:  # Skip malformed rows
                    continue
                theme = WeeklyTheme(
                    id=row[0],
                    week_start=datetime.fromisoformat(row[1]) if row[1] else None,
                    provider=row[2],
                    theme_name=row[3],
                    description=row[4],
                    relevance_score=row[5],
                    update_count=row[6]
                )
                db.session.add(theme)
    
    db.session.commit()

@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })
    
    # Create tables and context
    with app.app_context():
        db.create_all()
        populate_test_data(db)  # Load test data from JSON
        yield app
        db.drop_all()

@pytest.fixture(scope="session")
def flask_server(app):
    """Start Flask server for testing."""
    from threading import Thread
    server = Thread(target=lambda: app.run(port=5000))
    server.daemon = True
    server.start()
    yield "http://localhost:5000"