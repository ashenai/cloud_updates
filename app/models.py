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
    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.DateTime, nullable=False)
    week_end = db.Column(db.DateTime, nullable=False)
    aws_updates = db.Column(db.Integer, default=0)
    azure_updates = db.Column(db.Integer, default=0)
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WeeklyInsight {self.week_start} to {self.week_end}>'
