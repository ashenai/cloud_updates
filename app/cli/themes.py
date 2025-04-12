"""CLI commands for managing themes."""
import click
from datetime import datetime, timedelta
from flask.cli import with_appcontext
from app.models import Update, WeeklyTheme
from app.utils.theme_analyzer import ThemeAnalyzer, get_week_start
from app import db

@click.group()
def themes():
    """Manage weekly themes."""
    pass

@themes.command()
@click.option('--week', default=None, help='Week to generate themes for (YYYY-MM-DD)')
@with_appcontext
def generate(week=None):
    """Generate weekly themes from updates."""
    if week:
        week_start = get_week_start(datetime.strptime(week, '%Y-%m-%d'))
    else:
        week_start = get_week_start(datetime.utcnow())
    
    # Get updates for the week
    updates = Update.query.filter(
        Update.published_date >= week_start,
        Update.published_date < week_start + timedelta(days=7)
    ).all()
    
    if not updates:
        click.echo('No updates found for the selected week.')
        return
    
    # Delete existing themes for this week
    WeeklyTheme.query.filter_by(week_start=week_start).delete()
    
    # Generate new themes
    analyzer = ThemeAnalyzer()
    themes = analyzer.generate_themes(updates)
    
    # Save themes
    for theme in themes:
        theme_obj = WeeklyTheme(
            week_start=week_start,
            provider=theme['provider'],
            theme_name=theme['name'],
            description=theme['description'],
            relevance_score=theme['score'],
            update_count=theme['update_count']
        )
        db.session.add(theme_obj)
    
    db.session.commit()
    click.echo(f'Generated {len(themes)} themes for week of {week_start.strftime("%b %d, %Y")}.')
