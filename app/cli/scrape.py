"""CLI commands for scraping updates."""
import click
from flask.cli import with_appcontext
from app.scraper.aws_scraper import AWSScraper
from app.scraper.azure_scraper import AzureScraper

@click.group()
def scrape():
    """Scrape updates from cloud providers."""
    pass

@scrape.command()
@with_appcontext
def aws():
    """Scrape AWS updates."""
    scraper = AWSScraper()
    scraper.scrape()
    click.echo('Successfully scraped AWS updates.')

@scrape.command()
@with_appcontext
def azure():
    """Scrape Azure updates."""
    scraper = AzureScraper()
    scraper.scrape()
    click.echo('Successfully scraped Azure updates.')
