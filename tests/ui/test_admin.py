"""UI tests for admin functionality."""
import pytest
from playwright.sync_api import expect, Page

@pytest.fixture
def admin_page(page: Page, flask_server: str):
    """Setup admin authentication and return admin page."""
    # Navigate to admin page
    page.goto(f"{flask_server}/admin")
    yield page

def test_admin_page_loads(admin_page: Page):
    """Test admin page loads with maintenance options."""
    # Verify page title
    expect(admin_page).to_have_title("Admin - Cloud Updates")
    
    # Check for maintenance section
    maintenance_header = admin_page.locator('h2:text("Maintenance")')
    expect(maintenance_header).to_be_visible()
    
    # Verify scraping buttons exist
    expect(admin_page.locator('button:text("Fetch AWS Updates")')).to_be_visible()
    expect(admin_page.locator('button:text("Fetch Azure Updates")')).to_be_visible()

def test_theme_analysis(admin_page: Page):
    """Test theme analysis functionality."""
    # Click Theme Analysis tab/section
    theme_tab = admin_page.locator('text=Theme Analysis')
    theme_tab.click()
    
    # Verify theme analysis elements
    expect(admin_page.locator('text="Theme Analysis Results"')).to_be_visible()
    
    # Test theme analysis button
    analyze_button = admin_page.locator('button:text("Analyze Themes")')
    expect(analyze_button).to_be_visible()

def test_maintenance_operations(admin_page: Page):
    """Test maintenance operations in admin panel."""
    # Test duplicate cleaning
    clean_button = admin_page.locator('button:text("Clean Duplicates")')
    expect(clean_button).to_be_visible()
    
    # Check for confirmation dialogs when clicking maintenance buttons
    clean_button.click()
    expect(admin_page.locator('text="Are you sure?"')).to_be_visible()

def test_search_page(page: Page, flask_server: str):
    """Test search page functionality."""
    # Navigate to search page
    page.goto(f"{flask_server}/search")
    
    # Check page title and search form
    expect(page).to_have_title("Search - Cloud Updates")
    expect(page.locator('#search-form')).to_be_visible()