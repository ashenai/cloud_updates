"""
Copyright 2025 Aavind K Shenai

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

DISCLAIMER:
This code was generated using artificial intelligence. While efforts have been made
to ensure its accuracy and functionality, users should:
1. Review and test the code thoroughly before deployment
2. Be aware that AI-generated code may contain unexpected behaviors
3. Use this code at their own risk
4. Not rely on this code for critical systems without proper validation
"""

"""Flask application factory."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Get absolute path for database
    instance_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance'))
    db_path = os.path.join(instance_path, 'cloud_updates.db')
    
    # Ensure instance folder exists
    try:
        os.makedirs(instance_path, exist_ok=True)
    except OSError:
        pass
        
    # Force database name before loading config
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    
    # Set secret key with priority:
    # 1. GitHub Actions secret (FLASK_SECRET_KEY)
    # 2. Environment variable (SECRET_KEY)
    # 3. Value from .env file
    # 4. Development fallback (never use in production)
    app.config['SECRET_KEY'] = (
        os.environ.get('FLASK_SECRET_KEY') or  # GitHub Actions secret
        os.environ.get('SECRET_KEY') or        # Regular environment variable
        'dev-temporary-key-replace-in-production'  # Fallback for development only
    )
    print(f"Setting database path to: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Load rest of config but preserve database URI and secret key
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    secret_key = app.config['SECRET_KEY']
    app.config.from_object(config_class)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SECRET_KEY'] = secret_key

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.routes import init_routes, nl_search_bp # Import the new blueprint
    init_routes(app)
    app.register_blueprint(nl_search_bp) # Register the new blueprint

    # Initialize CLI commands
    from app.cli import init_app as init_cli
    init_cli(app)

    # Create tables if they don't exist
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
            print(f"Final database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        except Exception as e:
            print(f"Error creating database tables: {e}")
    
    return app
