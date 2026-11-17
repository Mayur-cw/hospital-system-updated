import uuid

from flask import Flask, g, request

from hms.cli import register_cli
from hms.config import get_config
from hms.extensions import csrf, db, login_manager, migrate
from hms.filters import register_filters
from hms.models.user import User


def create_app(config_object=None):
    """Application factory for Hospital Management System (A-01)."""
    app = Flask(__name__, template_folder='templates', static_folder='static')

    if config_object:
        app.config.from_object(config_object)
    else:
        app.config.from_object(get_config())

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Conditionally enable CSRF
    if app.config.get('WTF_CSRF_ENABLED', True):
        csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please login to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Request ID and tracing hook
    @app.before_request
    def set_request_id():
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

    @app.after_request
    def append_request_id(response):
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        return response

    # Register custom Jinja filters (A-04)
    register_filters(app)

    # Register Blueprints
    from hms.routes.admin import admin_bp
    from hms.routes.auth import auth_bp
    from hms.routes.doctor import doctor_bp
    from hms.routes.main import main_bp
    from hms.routes.patient import patient_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Register CLI
    register_cli(app)

    return app
