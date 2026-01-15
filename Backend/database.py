import os
from models import db

def init_database(app):
    """Initialize database"""
    with app.app_context():
        # Create uploads folder if it doesn't exist
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # Create all tables
        db.create_all()
        print("Database initialized successfully!")

def reset_database(app):
    """Reset database (use with caution!)"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset successfully!")