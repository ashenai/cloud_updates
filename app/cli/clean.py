"""
Command-line utility to clean AWS and Azure updates.
"""
import click
from flask.cli import with_appcontext
from app import db
from app.models import Update
from app.utils.clean_updates import clean_aws_updates, clean_azure_updates

@click.group(name='clean')
def cli():
    """Clean AWS and Azure updates."""
    pass

@cli.command()
@click.option('--delete-old', is_flag=True, help='Delete updates older than 90 days')
@with_appcontext
def azure(delete_old):
    """Clean Azure updates by removing duplicates and optionally old entries."""
    updates = Update.query.filter_by(provider='azure').all()
    removed = clean_azure_updates(updates, delete_old=delete_old)
    click.echo(f'Cleaned {removed} Azure updates.')

@cli.command()
@click.option('--delete-old', is_flag=True, help='Delete updates older than 90 days')
@with_appcontext
def aws(delete_old):
    """Clean AWS updates by removing duplicates and optionally old entries."""
    updates = Update.query.filter_by(provider='aws').all()
    removed = clean_aws_updates(updates, delete_old=delete_old)
    click.echo(f'Cleaned {removed} AWS updates.')

@cli.command()
@click.option('--delete-old', is_flag=True, help='Delete updates older than 90 days')
@with_appcontext
def all(delete_old):
    """Clean both AWS and Azure updates."""
    # Clean Azure updates
    azure_updates = Update.query.filter_by(provider='azure').all()
    azure_removed = clean_azure_updates(azure_updates, delete_old=delete_old)
    click.echo(f'Cleaned {azure_removed} Azure updates.')
    
    # Clean AWS updates
    aws_updates = Update.query.filter_by(provider='aws').all()
    aws_removed = clean_aws_updates(aws_updates, delete_old=delete_old)
    click.echo(f'Cleaned {aws_removed} AWS updates.')
    
    total_removed = azure_removed + aws_removed
    click.echo(f'Total updates cleaned: {total_removed}')

if __name__ == '__main__':
    cli()
