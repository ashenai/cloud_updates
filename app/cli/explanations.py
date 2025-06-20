"""
Command line utility for generating explanations for updates.
"""
import click
from flask.cli import with_appcontext
from app import db
from app.models import Update
from app.utils.update_analyzer import format_explanation_text
from anthropic import Anthropic
import os
import time
from random import uniform

@click.command('generate_explanations')
@with_appcontext
@click.option('--force-generation', is_flag=True, help='Force regeneration of explanations for all updates')
@click.option('--show-formatted', is_flag=True, help='Show a sample of formatted explanations with paragraph detection')
def generate_explanations(force_generation, show_formatted):
    """Generate explanations for updates using Claude."""
    try:        # Build query for updates without explanations or all updates if force_generation is true
        query = Update.query
        if not force_generation:
            query = query.filter(
                db.or_(
                    Update.explanation.is_(None),
                    Update.explanation == ''
                )
            )
        
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
                prompt = f"provide brief explanation for '{update.title}' ignore keywords like \"in preview\" or \"launched\" or \"retired\" or \"in development\" from title for generating description. Don't mention status like \"Public Preview\" or \"Private Preview\" or \"Generally Available\"."
                
                # Implement retry logic with exponential backoff
                max_retries = 5
                base_delay = 1  # Start with 1 second delay
                
                for attempt in range(max_retries):
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
                        
                        # Store the raw explanation - we'll format it during retrieval
                        # This approach ensures compatibility with both old and new code
                        raw_explanation = explanation.strip()
                        
                        # Note: We're not applying formatting here because:
                        # 1. We want to store the raw text in the database
                        # 2. The get_update_explanation route will handle formatting on retrieval
                        # 3. This preserves compatibility with both old and new approaches
                        
                        update.explanation = raw_explanation
                        processed += 1
                        break  # Success! Break the retry loop
                        
                    except Exception as e:
                        if 'overloaded_error' in str(e):
                            if attempt < max_retries - 1:  # Don't wait after the last attempt
                                delay = base_delay * (2 ** attempt) + uniform(0, 0.1)  # Add small random jitter
                                click.echo(f'\nAPI overloaded, retrying in {delay:.1f} seconds... (Attempt {attempt + 1}/{max_retries})', err=True)
                                time.sleep(delay)
                                continue
                        
                        click.echo(f'\nError generating explanation for update {update.id}: {str(e)}', err=True)
                        break  # Break on non-overload errors or final attempt
                
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
            
            # Show sample formatted explanations if requested
            if show_formatted and processed > 0:
                click.echo("\nSample formatted explanations with paragraph detection:")
                
                # Show up to 3 samples
                sample_updates = updates[:min(3, processed)]
                for i, update in enumerate(sample_updates):
                    if update.explanation:
                        click.echo(f"\n--- Example {i+1}: {update.title} ---")
                        click.echo("\nRaw text stored in database:")
                        click.echo(update.explanation[:200] + "..." if len(update.explanation) > 200 else update.explanation)
                        
                        click.echo("\nFormatted with spaCy paragraph detection (what users will see):")
                        formatted = format_explanation_text(update.explanation)
                        # Remove HTML tags for CLI display
                        formatted_text = formatted.replace('<p>', '\n\n').replace('</p>', '').strip()
                        click.echo(formatted_text[:300] + "..." if len(formatted_text) > 300 else formatted_text)
                        click.echo("\n" + "-" * 60)
                
        except Exception as commit_error:
            db.session.rollback()
            click.echo(f'\nError saving explanations: {str(commit_error)}', err=True)
            
    except Exception as e:
        click.echo(f'Error: {str(e)}', err=True)
