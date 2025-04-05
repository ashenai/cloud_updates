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

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Initialize SQLAlchemy
db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder='templates')
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cloud_updates.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Set a secure secret key for sessions
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Initialize extensions
    db.init_app(app)
    
    with app.app_context():
        # Import routes here to avoid circular imports
        from . import routes
        
        # Initialize routes
        routes.init_routes(app)
        
        # Create tables only if they don't exist
        db.create_all()
        
        # Print message only on first creation
        if not os.path.exists(os.path.join(os.path.dirname(app.instance_path), 'instance/cloud_updates.db')):
            print("Database tables created successfully!")
    
    return app
