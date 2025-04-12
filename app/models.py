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

from app import db
from datetime import datetime
import json

class Update(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(10), nullable=False)  # 'aws' or 'azure'
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(500))
    published_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    _categories = db.Column('categories', db.Text, default='[]')  # JSON array of categories
    _update_types = db.Column('update_types', db.Text, default='[]')  # JSON array of update types
    product_name = db.Column(db.String(100))  # Name of the AWS/Azure product
    
    __table_args__ = (
        db.UniqueConstraint('provider', 'title', 'published_date', name='unique_update'),
    )
    
    @property
    def categories(self):
        return json.loads(self._categories)
    
    @categories.setter
    def categories(self, value):
        if isinstance(value, str):
            self._categories = json.dumps([value])
        elif isinstance(value, (list, tuple)):
            self._categories = json.dumps(list(value))
        else:
            self._categories = '[]'
    
    @property
    def update_types(self):
        return json.loads(self._update_types)
    
    @update_types.setter
    def update_types(self, value):
        if isinstance(value, str):
            self._update_types = json.dumps([value])
        elif isinstance(value, (list, tuple)):
            self._update_types = json.dumps(list(value))
        else:
            self._update_types = '[]'

    def __repr__(self):
        return f'<Update {self.provider}:{self.title}>'

class WeeklyInsight(db.Model):
    """Weekly insights from updates."""
    __tablename__ = 'weekly_insights'

    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.DateTime, nullable=False)
    week_end = db.Column(db.DateTime, nullable=False)
    aws_updates = db.Column(db.Integer, default=0)
    azure_updates = db.Column(db.Integer, default=0)
    aws_top_products = db.Column(db.JSON)  # Store top 5 AWS products and their counts
    azure_top_categories = db.Column(db.JSON)  # Store top 5 Azure categories and their counts
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WeeklyInsight {self.week_start} - {self.week_end}>'

class WeeklyTheme(db.Model):
    """Model for weekly themes of cloud updates."""
    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.DateTime, nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # 'aws' or 'azure'
    theme_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    relevance_score = db.Column(db.Float)  # How relevant/important this theme is (0-1)
    update_count = db.Column(db.Integer)  # Number of updates in this theme
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WeeklyTheme {self.provider} - {self.theme_name} ({self.week_start.strftime("%Y-%m-%d")})>'
