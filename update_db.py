"""
Script to update the database schema with new columns for Azure updates.
"""
from app import create_app, db
from sqlalchemy import Column, Text
from sqlalchemy.sql import text

def update_database_schema():
    """Add new columns to the Update table if they don't exist."""
    # Create the app instance
    app = create_app()
    
    with app.app_context():
        # Check if the columns already exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('update')]
        
        # Add status column if it doesn't exist
        if 'status' not in columns:
            print("Adding 'status' column to Update table...")
            # Add the column - quote the table name since 'update' is a SQL keyword
            db.session.execute(text('ALTER TABLE "update" ADD COLUMN status TEXT DEFAULT \'[]\''))
            db.session.commit()
            print("Status column added successfully!")
        else:
            print("'status' column already exists in Update table.")
            
        # Add product_names column if it doesn't exist
        if 'product_names' not in columns:
            print("Adding 'product_names' column to Update table...")
            # Add the column - quote the table name since 'update' is a SQL keyword
            db.session.execute(text('ALTER TABLE "update" ADD COLUMN product_names TEXT DEFAULT \'[]\''))
            db.session.commit()
            print("Product_names column added successfully!")
        else:
            print("'product_names' column already exists in Update table.")

if __name__ == "__main__":
    update_database_schema()
    print("Database schema update complete!")
