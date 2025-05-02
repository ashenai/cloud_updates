import pytest
from datetime import datetime
from app.scraper.azure_scraper import AzureScraper

def test_clean_html():
    scraper = AzureScraper()
    html = """In late-April 2025, the following updates and enhancements were made to Azure SQL: The MSSQL extension for VS Code now includes Schema Compare in its April release—making it easier to compare database schemas, identify differences, and apply updates acros"""
    cleaned = scraper.clean_html(html)
    assert "Azure SQL" in cleaned
    assert "Schema Compare" in cleaned
    assert cleaned == html.strip()

def test_get_update_date():
    scraper = AzureScraper()
    
    entry = {
        'published': 'Wed, 30 Apr 2025 16:00:32 Z',
        'updated': '2025-04-30T16:00:32Z'
    }
    
    result = scraper.get_update_date(entry)
    assert result == datetime(2025, 4, 30, 16, 0, 32)

def test_parse_azure_update():
    """Test parsing of real Azure SQL update entry with proper category classification."""
    scraper = AzureScraper()
    
    entry = {
        'title': '[In preview] Public Preview: Azure SQL updates for late-April 2025',
        'link': 'https://azure.microsoft.com/updates?id=489702',
        'description': 'In late-April 2025, the following updates and enhancements were made to Azure SQL: The MSSQL extension for VS Code now includes Schema Compare in its April release—making it easier to compare database schemas, identify differences, and apply updates acros',
        'published': 'Wed, 30 Apr 2025 16:00:32 Z',
        'updated': '2025-04-30T16:00:32Z',
        'categories': ['In preview', 'Databases', 'Hybrid + multicloud', 'Azure SQL Database', 'Features']
    }
    
    update = scraper.parse_entry(entry)
    
    # Basic fields
    assert update is not None
    assert update.title == entry['title']
    assert update.url == entry['link']
    assert update.description == entry['description']
    assert update.published_date == datetime(2025, 4, 30, 16, 0, 32)
    assert update.provider == 'azure'
    
    # Category classification validation
    assert update.status == ['In preview']  # Status tag
    assert 'Features' in update.update_types  # Update type
    
    # Product names (anything not in status_tags or update_types)
    assert 'Databases' in update.product_names
    assert 'Hybrid + multicloud' in update.product_names
    assert 'Azure SQL Database' in update.product_names
    assert len(update.product_names) == 3  # Only these three should be products

def test_empty_entry_handling():
    scraper = AzureScraper()
    
    empty_entry = {
        'title': '',
        'link': '',
        'description': '',
        'published': None,
        'updated': None,
        'categories': []
    }
    
    update = scraper.parse_entry(empty_entry)
    assert update is None, "Should return None for empty entry"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])