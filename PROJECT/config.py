import os

class Config:
    # Use environment variable for secret key; fallback for dev only
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hmsprojects_dev_key')
    
    # Database URI — set via env var in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'mysql://root:Mayur@localhost/hms')
    
    # Suppress warning
    SQLALCHEMY_TRACK_MODIFICATIONS = False