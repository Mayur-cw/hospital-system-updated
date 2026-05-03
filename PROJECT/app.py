# app.py
import os
from flask import Flask
from flask_login import LoginManager

from config import Config
from models import db, User

# Import Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.patient import patient_bp
from routes.doctor import doctor_bp
from routes.main import main_bp

# App Initialization
app = Flask(__name__)
app.config.from_object(Config)

# Database Initialization
db.init_app(app)

# Login Manager Initialization
login_manager = LoginManager(app)
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
# The URL prefix means every route in admin.py will automatically start with /admin
app.register_blueprint(admin_bp, url_prefix='/admin')

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'true').lower() == 'true')