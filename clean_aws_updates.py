from app import create_app, db
from app.models import Update

def clean_aws_updates():
    app = create_app()
    with app.app_context():
        # Delete all existing AWS updates
        db.session.query(Update).filter_by(provider='aws').delete()
        db.session.commit()
        print('Successfully deleted all AWS updates')

if __name__ == '__main__':
    clean_aws_updates()
