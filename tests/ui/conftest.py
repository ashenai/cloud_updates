"""Playwright test configuration."""
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
import os
import sys
import json
import subprocess
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.models import db, Update, WeeklyInsight, WeeklyTheme

# Ensure Playwright browsers are installed
def pytest_configure(config):
    """Install Playwright browsers before tests run."""
    try:
        print("Installing Playwright browsers...")
        try:
            import playwright
            print(f"Playwright version: {playwright.__version__}")
        except ImportError:
            print("Playwright module not found in Python environment")
            
        # Use subprocess with Python module to ensure correct Python environment
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--with-deps"],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Playwright installation output: {result.stdout}")
        print("Playwright browsers installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing Playwright browsers: {e}")
        print(f"Error output: {e.stderr if hasattr(e, 'stderr') else 'No error output'}")
    except Exception as e:
        print(f"Unexpected error installing Playwright browsers: {e}")
        import traceback
        traceback.print_exc()

def populate_test_data(db):
    """Populate database with test data from cloud_updates.json."""
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cloud_updates.json')
    
    try:
        print(f"Loading test data from: {json_path}")
        print(f"File exists: {os.path.exists(json_path)}")
        
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Test data file not found: {json_path}")
        
        # Process JSON file safely
        with open(json_path, 'r', encoding='utf-8') as f:
            # Read the file
            content = f.read()
            
            # Check if there's a BOM at the start of the file
            if content.startswith('\ufeff'):
                print("BOM detected at start of file, removing...")
                content = content[1:]
                
            # Parse the JSON directly - our test confirmed no comment lines
            try:
                data = json.loads(content)
                print("JSON data loaded successfully")
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Error at position {e.pos}: {content[max(0, e.pos-20):min(len(content), e.pos+20)]}")
                
                # Fall back to line filtering approach
                print("Falling back to line filtering approach")
                with open(json_path, 'r', encoding='utf-8') as f2:
                    lines = []
                    for line in f2:
                        if not line.strip().startswith('//'):
                            lines.append(line)
                    content = ''.join(lines)
                    data = json.loads(content)
    except Exception as e:
        print(f"Error loading test data: {e}")
        raise
    
    # Helper function to safely parse JSON strings
    def safe_json_loads(json_str, default_value=None):
        """Safely parse JSON string, returning default_value if parsing fails."""
        if not json_str:
            return default_value
            
        # Check if it looks like a timestamp (common false positive for JSON data)
        if isinstance(json_str, str) and ' ' in json_str and '-' in json_str and ':' in json_str:
            if json_str.count(':') >= 2 and json_str.count('-') >= 2:
                print(f"Skipping JSON parsing for timestamp-like string: {json_str}")
                return default_value
                
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e} in string: {json_str}")
            return default_value
    
    # Process each table from the backup
    for table in data['objects']:
        if table['name'] == 'update':
            for row in table['rows']:
                if not isinstance(row, list) or len(row) < 12:  # Skip malformed rows
                    continue                  # Process the explanation text - convert "\r\n\r\n" into paragraph breaks
                explanation = None
                if len(row) > 12 and row[12]:
                    # Replace Windows-style double line breaks with single newlines for paragraphs
                    explanation = row[12].replace('\r\n\r\n', '\n\n')
                    # Also handle Unix-style double line breaks
                    explanation = explanation.replace('\n\n\n\n', '\n\n')
                
                update = Update(
                    id=row[0],
                    provider=row[1],
                    title=row[2],
                    description=row[3],
                    url=row[4],
                    published_date=datetime.fromisoformat(row[5]) if row[5] else None,
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    categories=safe_json_loads(row[7], []),
                    update_types=safe_json_loads(row[8], []),
                    product_name=row[9],
                    status=safe_json_loads(row[10], []),
                    product_names=safe_json_loads(row[11], []),
                    explanation=explanation  # Use our processed explanation text
                )
                db.session.add(update)
        
        elif table['name'] == 'weekly_insights':  # Using weekly_insights instead of weekly_insight
            for row in table['rows']:
                if not isinstance(row, list) or len(row) < 7:  # Skip malformed rows
                    continue
                
                # Safely parse JSON fields
                try:
                    aws_products = safe_json_loads(row[5], {})
                    azure_categories = safe_json_loads(row[6], {})
                    
                    insight = WeeklyInsight(
                        id=row[0],
                        week_start=datetime.fromisoformat(row[1]) if row[1] else None,
                        week_end=datetime.fromisoformat(row[2]) if row[2] else None,
                        aws_updates=row[3],
                        azure_updates=row[4],
                        aws_top_products=aws_products,
                        azure_top_categories=azure_categories
                    )
                    db.session.add(insight)
                except Exception as e:
                    print(f"Error creating WeeklyInsight from row {row}: {e}")
                    continue
        
        elif table['name'] == 'weekly_theme':
            for row in table['rows']:
                if not isinstance(row, list) or len(row) < 7:  # Skip malformed rows
                    continue
                    
                try:
                    # Use our safe JSON parser for the services field
                    services = safe_json_loads(row[7] if len(row) > 7 else None, [])
                    
                    theme = WeeklyTheme(
                        id=row[0],
                        week_start=datetime.fromisoformat(row[1]) if row[1] else None,
                        provider=row[2],
                        theme_name=row[3],
                        description=row[4],
                        relevance_score=row[5],
                        update_count=row[6],
                        services=services
                    )
                    db.session.add(theme)
                except Exception as e:
                    print(f"Error creating WeeklyTheme from row {row}: {e}")
                    continue
    
    db.session.commit()

@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })
    
    # Create app without setting up tables yet
    return app
    
@pytest.fixture(scope="function")
def app_with_data(app):
    """Create a fresh database with test data for each test."""
    with app.app_context():
        # Create fresh tables for each test
        db.create_all()
        
        # Clear any existing data (in case tables already exist)
        db.session.query(Update).delete()
        db.session.query(WeeklyInsight).delete()
        db.session.query(WeeklyTheme).delete()
        db.session.commit()
        
        # Load test data
        populate_test_data(db)
        
        yield app
        
        # Clean up after the test
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope="session")
def flask_server(app):
    """Start Flask server for testing."""
    from threading import Thread
    from werkzeug.serving import make_server
    
    server = make_server('127.0.0.1', 0, app)
    server_thread = Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    yield f"http://{server.server_address[0]}:{server.server_address[1]}"
    
    server.shutdown()

@pytest.fixture(scope="session")
def browser():
    """Create a browser instance."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            browser.close()

@pytest.fixture(scope="function")
def page(browser, app_with_data, flask_server):
    """Create a new page for each test."""
    context = browser.new_context()
    page = context.new_page()
    
    # Pass the server URL for navigation
    page.server_url = flask_server
    
    yield page
    
    # Clean up after test
    context.close()