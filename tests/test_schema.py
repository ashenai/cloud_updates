"""
Test database schema and test data loading.
"""
import pytest
from app import create_app
from app.models import db, Update, WeeklyTheme
from tests.ui.conftest import populate_test_data

def test_schema():
    """Test if the schema works correctly with test data."""
    # Create test app
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })
    
    # Create tables and load test data
    with app.app_context():
        db.create_all()
        populate_test_data(db)
        
        # Check Update model
        update = Update.query.first()
        assert update is not None, "Failed to load test updates"
        assert hasattr(update, 'explanation'), "Update model missing explanation field"
        
        # Check WeeklyTheme model
        theme = WeeklyTheme.query.first()
        assert theme is not None, "Failed to load test themes"
        assert hasattr(theme, 'services'), "WeeklyTheme model missing services field"
