"""
CLI commands for the cloud_updates application.
"""
from .clean import clean
from .themes import themes
from .explanations import generate_explanations

def init_app(app):
    """Register CLI commands with the app."""
    app.cli.add_command(clean)
    app.cli.add_command(themes)
    app.cli.add_command(generate_explanations)
