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

"""
Flask application factory.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from datetime import datetime

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Get the base directory
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'instance', 'cloud_updates.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev-key-please-change-in-production'
    app.config['UPDATES_PER_PAGE'] = 20
    app.config['MAX_SEARCH_RESULTS'] = 100
    app.config['UPDATE_RETENTION_DAYS'] = 90
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import routes here to avoid circular imports
    from app.routes import init_routes
    init_routes(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Print message only on first creation
        if not os.path.exists(os.path.join(base_dir, 'instance', 'cloud_updates.db')):
            print("Database tables created successfully!")
    
    # Register CLI commands
    from app.cli import clean_cli
    app.cli.add_command(clean_cli)
    
    return app
