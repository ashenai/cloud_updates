"""
Check updates in database that need explanations.
"""
import os
import sys

# Add the project root to PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import Update

def check_explanations():
    app = create_app()
    with app.app_context():        # Count total updates
        total_updates = Update.query.count()
        
        # Count updates without explanations (NULL or empty string)
        missing_explanations = Update.query.filter(
            db.or_(
                Update.explanation.is_(None),
                Update.explanation == ''
            )
        ).all()
        
        print(f"\nTotal updates in database: {total_updates}")
        print(f"Updates missing explanations (NULL or empty): {len(missing_explanations)}")
        
        # Print some sample updates without explanations
        if missing_explanations:
            print("\nSample updates missing explanations:")
            for update in missing_explanations[:3]:
                print(f"- {update.title} (ID: {update.id})")
                print(f"  Explanation value: {repr(update.explanation)}")

if __name__ == '__main__':
    check_explanations()
