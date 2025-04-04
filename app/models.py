from datetime import datetime
from app import db

class Update(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(20), nullable=False)  # 'aws' or 'azure'
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(500), nullable=False)
    published_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add unique constraint to prevent duplicates
    __table_args__ = (
        db.UniqueConstraint('provider', 'title', 'published_date', name='unique_update'),
    )
    
    def __repr__(self):
        return f'<Update {self.provider}:{self.title}>'

class WeeklyInsight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.DateTime, nullable=False)
    week_end = db.Column(db.DateTime, nullable=False)
    aws_updates = db.Column(db.Integer, default=0)
    azure_updates = db.Column(db.Integer, default=0)
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WeeklyInsight {self.week_start} to {self.week_end}>'
