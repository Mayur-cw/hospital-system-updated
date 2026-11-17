import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Base application configuration."""
    APP_ENV = os.environ.get('APP_ENV', 'development').lower()
    FLASK_DEBUG = False
    TESTING = False

    # Secret Key
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    # Session / Cookie safety defaults (S-07)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 7200  # 2 hours
    SESSION_PROTECTION = 'strong'

    # Security / Talisman Settings (S-08)
    FORCE_HTTPS = False
    CSP_DIRECTIVES = None

    # Rate Limiting Settings (S-04)
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_STRATEGY = 'fixed-window'

    # Clinical, Scheduling & Regional Settings (A-03, A-04)
    TIMEZONE = os.environ.get('HOSPITAL_TIMEZONE', 'Asia/Kolkata')
    SLOT_DURATION_MINUTES = int(os.environ.get('SLOT_DURATION_MINUTES', '30'))
    CANCELLATION_WINDOW_HOURS = int(os.environ.get('CANCELLATION_WINDOW_HOURS', '2'))
    REMINDER_LEAD_HOURS = int(os.environ.get('REMINDER_LEAD_HOURS', '24'))
    PAYMENT_GATEWAY = os.environ.get('PAYMENT_GATEWAY', 'mock')
    MAIL_BACKEND = os.environ.get('MAIL_BACKEND', 'mailpit')

    # Reliability, Observability & Serving (R-01, R-06, R-07)
    BEHIND_PROXY = os.environ.get('BEHIND_PROXY', 'false').lower() in ('true', '1', 't')
    ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """Development configuration with safe defaults."""
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1', 't')
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('DEV_SECRET_KEY') or 'dev-insecure-secret-key-change-me'

    # Fallback to local SQLite development database if DATABASE_URL is not set
    if not os.environ.get('DATABASE_URL'):
        instance_dir = BASE_DIR / 'instance'
        instance_dir.mkdir(exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{instance_dir / 'hms_dev.db'}"
    else:
        raw_db_url = os.environ.get('DATABASE_URL')
        if 'mysql://root:Mayur' in raw_db_url:
            raise RuntimeError(
                "CRITICAL SECURITY BLOCKED: Prohibited legacy hardcoded root MySQL connection string detected."
            )
        SQLALCHEMY_DATABASE_URI = raw_db_url


class TestingConfig(Config):
    """Testing configuration for automated tests."""
    TESTING = True
    FLASK_DEBUG = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SECRET_KEY = 'test-secret-key-for-automated-suites'
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')


class ProductionConfig(Config):
    """Strict fail-closed production configuration."""
    FLASK_DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    FORCE_HTTPS = True
    BEHIND_PROXY = True
    RATELIMIT_STORAGE_URI = os.environ.get('REDIS_URL', 'memory://')

    def __init__(self):
        super().__init__()
        secret = os.environ.get('SECRET_KEY')
        if not secret or secret in ('hmsprojects_dev_key', 'dev-insecure-secret-key-change-me'):
            raise RuntimeError(
                "CRITICAL: Refusing to start in production without a secure, cryptographically random SECRET_KEY environment variable."
            )
        self.SECRET_KEY = secret

        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise RuntimeError(
                "CRITICAL: Refusing to start in production without a valid DATABASE_URL environment variable."
            )
        if 'mysql://root:Mayur' in db_url or 'root:' in db_url:
            raise RuntimeError(
                "CRITICAL: Refusing to start in production with default or root database credentials."
            )
        self.SQLALCHEMY_DATABASE_URI = db_url


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}

def get_config(env_name=None):
    """Retrieve configuration object by environment name."""
    env = (env_name or os.environ.get('APP_ENV') or os.environ.get('FLASK_ENV') or 'development').lower()
    config_cls = config_by_name.get(env, DevelopmentConfig)
    if env == 'production':
        return config_cls()
    return config_cls
