import uuid

from flask import Flask, g, render_template, request
from flask_wtf.csrf import CSRFError
from markupsafe import Markup

from hms.cli import register_cli
from hms.config import get_config
from hms.extensions import csrf, db, limiter, login_manager, migrate, talisman
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
    csrf.init_app(app)

    # Initialize Limiter (S-04)
    limiter.init_app(app)
    limiter.enabled = app.config.get('RATELIMIT_ENABLED', True)

    # Initialize Talisman (S-08)
    talisman.init_app(
        app,
        force_https=app.config.get('FORCE_HTTPS', False),
        content_security_policy=app.config.get('CSP_DIRECTIVES', None),
        frame_options='SAMEORIGIN',
        referrer_policy='strict-origin-when-cross-origin'
    )

    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please login to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Request ID and tracing hook (S-09)
    @app.before_request
    def set_request_id():
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

    @app.after_request
    def append_security_and_tracing_headers(response):
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id

        # Cache-Control: no-store on sensitive clinical & financial data (S-08)
        sensitive_prefixes = ('/bills', '/records', '/profile', '/admin', '/discharge', '/edit_record', '/add_record')
        if any(request.path.startswith(p) for p in sensitive_prefixes):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
        return response

    # Template macro csrf_field (S-01)
    @app.template_global()
    def csrf_field():
        if not app.config.get('WTF_CSRF_ENABLED', True):
            return Markup('')
        try:
            from flask_wtf.csrf import generate_csrf
            return Markup(f'<input type="hidden" name="csrf_token" value="{generate_csrf()}">')
        except Exception:
            return Markup('')

    # Custom Error Handlers (S-09)
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        req_id = getattr(g, 'request_id', None)
        if request.is_json or request.path.startswith('/api/'):
            return {"error": "CSRF validation failed", "description": e.description, "request_id": req_id}, 400
        return render_template('errors/400.html', message=f"Security verification failed: {e.description}. Please refresh the page and try again.", request_id=req_id), 400

    @app.errorhandler(400)
    def handle_bad_request(e):
        req_id = getattr(g, 'request_id', None)
        if request.is_json or request.path.startswith('/api/'):
            return {"error": "Bad Request", "description": getattr(e, 'description', str(e)), "request_id": req_id}, 400
        return render_template('errors/400.html', message=getattr(e, 'description', None), request_id=req_id), 400

    @app.errorhandler(403)
    def handle_forbidden(e):
        req_id = getattr(g, 'request_id', None)
        if request.is_json or request.path.startswith('/api/'):
            return {"error": "Forbidden", "description": getattr(e, 'description', str(e)), "request_id": req_id}, 403
        return render_template('errors/403.html', message=getattr(e, 'description', None), request_id=req_id), 403

    @app.errorhandler(404)
    def handle_not_found(e):
        req_id = getattr(g, 'request_id', None)
        if request.is_json or request.path.startswith('/api/'):
            return {"error": "Not Found", "description": getattr(e, 'description', str(e)), "request_id": req_id}, 404
        return render_template('errors/404.html', message=getattr(e, 'description', None), request_id=req_id), 404

    @app.errorhandler(429)
    def handle_rate_limit(e):
        req_id = getattr(g, 'request_id', None)
        if request.is_json or request.path.startswith('/api/'):
            return {"error": "Rate limit exceeded", "description": getattr(e, 'description', str(e)), "request_id": req_id}, 429
        return render_template('errors/429.html', message=getattr(e, 'description', None), request_id=req_id), 429

    @app.errorhandler(500)
    def handle_server_error(e):
        req_id = getattr(g, 'request_id', None)
        if request.is_json or request.path.startswith('/api/'):
            return {"error": "Internal Server Error", "request_id": req_id}, 500
        return render_template('errors/500.html', request_id=req_id), 500

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
