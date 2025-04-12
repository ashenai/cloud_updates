"""Utility functions for scraping updates."""
from app.scraper.aws_scraper import AWSScraper
from app.scraper.azure_scraper import AzureScraper

def scrape_aws_updates():
    """Scrape AWS updates."""
    scraper = AWSScraper()
    return scraper.scrape()

def scrape_azure_updates():
    """Scrape Azure updates."""
    scraper = AzureScraper()
    return scraper.scrape()
