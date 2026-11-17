# app.py
import os
from flask import Flask
from flask_login import LoginManager

from config import get_config
from models import db, User

# Import Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.patient import patient_bp
from routes.doctor import doctor_bp
from routes.main import main_bp
from cli import register_cli

def create_app(config_object=None):
    """Application factory for Hospital OS."""
    application = Flask(__name__)
    if config_object:
        application.config.from_object(config_object)
    else:
        application.config.from_object(get_config())

    # Database Initialization
    db.init_app(application)

    # Login Manager Initialization
    login_manager = LoginManager(application)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please login to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    application.register_blueprint(main_bp)
    application.register_blueprint(auth_bp)
    application.register_blueprint(patient_bp)
    application.register_blueprint(doctor_bp)
    application.register_blueprint(admin_bp, url_prefix='/admin')

    # Register CLI Commands
    register_cli(application)

    return application

app = create_app()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1', 't')
    app.run(debug=debug_mode)
