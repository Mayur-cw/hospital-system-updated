import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Safe, environment-aware configuration for Hospital OS."""
    
    APP_ENV = os.environ.get('APP_ENV', 'development').lower()
    
    # Debug flag: False by default. NEVER allow True in production.
    if APP_ENV == 'production':
        FLASK_DEBUG = False
    else:
        FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1', 't')
        
    # Secret Key: strictly required in production
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('DEV_SECRET_KEY') or secrets.token_hex(32)
        
    # Database URI:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        instance_dir = BASE_DIR / 'instance'
        instance_dir.mkdir(exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{instance_dir / 'hms_dev.db'}"
    else:
        if 'mysql://root:Mayur' in DATABASE_URL:
            raise RuntimeError(
                "CRITICAL SECURITY BLOCKED: Prohibited legacy hardcoded root MySQL connection string detected."
            )
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = (APP_ENV == 'production')
    
    # Safety and Feature Flags
    DEMO_ONLY = os.environ.get('DEMO_ONLY', 'true').lower() in ('true', '1', 't')
    ENABLE_EXTERNAL_PAYMENTS = os.environ.get('ENABLE_EXTERNAL_PAYMENTS', 'false').lower() in ('true', '1', 't')
    ENABLE_ABDM_INTEGRATION = os.environ.get('ENABLE_ABDM_INTEGRATION', 'false').lower() in ('true', '1', 't')
    
    FACILITY_TIMEZONE = os.environ.get('FACILITY_TIMEZONE', 'Asia/Kolkata')
    WTF_CSRF_ENABLED = True

    @classmethod
    def validate(cls):
        """Enforces fail-closed validation for production startup."""
        current_env = os.environ.get('APP_ENV', cls.APP_ENV).lower()
        if current_env == 'production':
            secret = os.environ.get('SECRET_KEY')
            if not secret or secret in ('hmsprojects_dev_key', 'REPLACE_IN_LOCAL_ENV_ONLY'):
                raise RuntimeError(
                    "CRITICAL SECURITY FAILURE: SECRET_KEY environment variable is missing or insecure in production mode. "
                    "The application refuses to start."
                )
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                raise RuntimeError(
                    "CRITICAL SECURITY FAILURE: DATABASE_URL environment variable is missing in production mode. "
                    "Root database defaults are prohibited."
                )
