from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cloud_updates.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    from app import routes
    scheduler = routes.init_routes(app)  # Store the scheduler object
    app.scheduler = scheduler  # Attach it to the app for later use
    
    with app.app_context():
        db.create_all()
    
    return app
