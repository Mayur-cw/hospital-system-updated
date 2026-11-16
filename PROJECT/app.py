# PROJECT/app.py
import os
import sys
from pathlib import Path
from datetime import datetime

# Ensure PROJECT directory is in python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from flask import Flask, jsonify
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import db, User

# Import Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.patient import patient_bp
from routes.doctor import doctor_bp
from routes.main import main_bp
from routes.reception import reception_bp

csrf = CSRFProtect()
login_manager = LoginManager()

def create_app(config_class=Config):
    """Application Factory pattern for Hospital OS."""
    # Enforce strict startup security validation
    if hasattr(config_class, 'validate'):
        config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Extensions
    db.init_app(app)
    csrf.init_app(app)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please login to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(reception_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Global Context Processor
    @app.context_processor
    def inject_globals():
        return {
            'demo_only': app.config.get('DEMO_ONLY', True),
            'app_env': app.config.get('APP_ENV', 'development'),
            'facility_name': 'Metro General Hospital & OPD Center'
        }

    # Health & Readiness Check Endpoint
    @app.route('/health')
    def health_check():
        db_status = "healthy"
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

        status_code = 200 if db_status == "healthy" else 503
        return jsonify({
            "status": "UP" if db_status == "healthy" else "DEGRADED",
            "database": db_status,
            "mode": "DEMO_ONLY" if app.config.get('DEMO_ONLY', True) else "PRODUCTION",
            "environment": app.config.get('APP_ENV', 'development'),
            "timestamp": datetime.utcnow().isoformat()
        }), status_code

    return app

# Default application instance for development runners
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug_flag = app.config.get('FLASK_DEBUG', False)
    print(f"Hospital OS starting on http://127.0.0.1:{port} (Debug: {debug_flag})")
    app.run(host='127.0.0.1', port=port, debug=debug_flag)
