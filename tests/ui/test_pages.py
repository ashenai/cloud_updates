"""UI tests for Cloud Updates application."""
import pytest
from playwright.sync_api import expect, Page

def test_homepage(page: Page, flask_server: str):
    """Test homepage loads correctly with both AWS and Azure cards."""
    # Navigate to homepage
    print(f"Navigating to {flask_server}")
    page.goto(flask_server)
    
    # Debug - Take screenshot and print page content
    page.screenshot(path="homepage_debug.png")
    print("Page content:")
    print(page.content())
    
    # Debug - Check what links exist
    all_links = page.locator('a').all()
    print("All links on the page:")
    for link in all_links:
        try:
            print(f"Link text: '{link.inner_text()}', href: '{link.get_attribute('href')}'")
        except Exception as e:
            print(f"Error getting link info: {e}")
            
    # Check page title
    expect(page).to_have_title("Cloud Updates")
      # Verify AWS card with more specific selectors
    expect(page.locator('h2:has-text("AWS")')).to_be_visible()
    expect(page.locator('.btn:has-text("View All AWS Updates")')).to_be_visible()
    
    # Verify Azure card with more specific selectors
    expect(page.locator('h2:has-text("Azure")')).to_be_visible()
    expect(page.locator('.btn:has-text("View All Azure Updates")')).to_be_visible()

def test_aws_updates_page(page: Page, flask_server: str):
    """Test AWS Updates page loads correctly."""
    # Navigate to AWS updates page
    page.goto(f"{flask_server}/aws_updates")
    
    # Check page title
    expect(page).to_have_title("Cloud Updates")
    
    # Verify page header and content
    expect(page.locator('h1:text("AWS Updates")')).to_be_visible()

def test_azure_updates_page(page: Page, flask_server: str):
    """Test Azure Updates page loads correctly."""
    # Navigate to Azure updates page
    page.goto(f"{flask_server}/azure_updates")
    
    # Check page title
    expect(page).to_have_title("Cloud Updates")
    
    # Verify page header and content
    expect(page.locator('h1:text("Azure Updates")')).to_be_visible()

def test_search_functionality(page: Page, flask_server: str):
    """Test search functionality on the dedicated search page."""
    # Navigate to search page
    page.goto(f"{flask_server}/search")
    
    # Check page title and elements
    expect(page).to_have_title("Cloud Updates")
    expect(page.locator('h2:text("Semantic Search")')).to_be_visible()
    
    # Test empty search handling
    search_input = page.locator('input[name="q"]')
    expect(search_input).to_be_visible()
    expect(search_input).to_have_attribute("placeholder", "e.g., 'machine learning updates in AWS'")
    
    # Test search with no results
    search_input.fill("xyznonexistentquery123")
    page.locator('button:text("Search")').click()
    expect(page.locator('.alert-info:text("No results found")')).to_be_visible()
    
    # Test search with results
    search_input.fill("Lambda Functions")
    page.locator('button:text("Search")').click()
    
    # Wait for search results
    results_section = page.locator('.card').first
    expect(results_section).to_be_visible()
    
    # Check result card elements
    first_result = page.locator('.card').first
    expect(first_result.locator('.provider-badge')).to_be_visible()
    expect(first_result.locator('.card-title')).to_be_visible()
    expect(first_result.locator('.meta-tags')).to_be_visible()
    expect(first_result.locator('.text-muted')).to_be_visible()
    expect(first_result.locator('text=Relevance: ')).to_be_visible()   

    # Test preview modal functionality
    preview_button = first_result.locator('button:text("Preview")')
    expect(preview_button).to_be_visible()
    preview_button.click()
    
    # Get the previewModal ID
    modal_id = preview_button.get_attribute('data-bs-target')
    
    # Verify modal content using the specific modal ID
    modal = page.locator(f'{modal_id} .modal-content')
    expect(modal).to_be_visible()
    expect(modal.locator('.modal-title')).to_be_visible()
    expect(modal.locator('.meta-info')).to_be_visible()
    expect(modal.locator('a:text("Read Full Update")')).to_be_visible()
    
    # Close modal using the specific close button within this modal
    page.locator(f'{modal_id} .btn-close').click()
    expect(modal).not_to_be_visible()
    

def test_provider_specific_search(page: Page, flask_server: str):
    """Test provider-specific search queries."""
    page.goto(f"{flask_server}/search")
    
    # Test AWS-specific search
    search_input = page.locator('input[name="q"]')
    search_input.fill("AWS Lambda new features")
    page.locator('button:text("Search")').click()
    
    results = page.locator('.card')
    first_result = results.first
    expect(first_result.locator('.aws-badge')).to_be_visible()
    
    # Test Azure-specific search
    search_input.fill("Azure Functions updates")
    page.locator('button:text("Search")').click()
    
    results = page.locator('.card')
    first_result = results.first
    expect(first_result.locator('.azure-badge')).to_be_visible()