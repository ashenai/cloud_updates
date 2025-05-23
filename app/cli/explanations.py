"""
Command line utility for generating explanations for updates.
"""
import click
from flask.cli import with_appcontext
from app import db
from app.models import Update
from anthropic import Anthropic
import os

@click.command('generate_explanations')
@with_appcontext
@click.option('--force-generation', is_flag=True, help='Force regeneration of explanations for all updates')
def generate_explanations(force_generation):
    """Generate explanations for updates using Claude."""
    try:
        # Build query for updates without explanations or all updates if force_generation is true
        query = Update.query
        if not force_generation:
            query = query.filter(Update.explanation.is_(None))
        
        updates = query.order_by(Update.published_date.desc()).all()
        total_updates = len(updates)
        
        if not updates:
            click.echo('No updates found that need explanations.')
            return
        
        click.echo(f'Found {total_updates} updates to process')
        
        # Initialize Claude client
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        if not os.getenv('ANTHROPIC_API_KEY'):
            click.echo('Error: ANTHROPIC_API_KEY environment variable not set', err=True)
            return

        processed = 0
        with click.progressbar(updates, label='Generating explanations') as bar:
            for update in bar:
                prompt = f"provide brief explanation for: '{update.title}'."
                
                try:
                    message = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=1000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    explanation = ""
                    for content in message.content:
                        if hasattr(content, 'text'):
                            explanation += content.text
                        elif isinstance(content, str):
                            explanation += content
                    
                    update.explanation = explanation.strip()
                    processed += 1
                    
                except Exception as e:
                    click.echo(f'\nError generating explanation for update {update.id}: {str(e)}', err=True)
                    continue
                
                # Commit in batches of 10
                if processed % 10 == 0:
                    try:
                        db.session.commit()
                    except Exception as commit_error:
                        click.echo(f'\nError committing batch: {str(commit_error)}', err=True)
                        db.session.rollback()
        
        # Final commit for remaining changes
        try:
            db.session.commit()
            click.echo(f'\nSuccessfully generated {processed} explanations.')
        except Exception as commit_error:
            db.session.rollback()
            click.echo(f'\nError saving explanations: {str(commit_error)}', err=True)
            
    except Exception as e:
        click.echo(f'Error: {str(e)}', err=True)
