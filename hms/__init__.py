import uuid

from flask import Flask, abort, g, jsonify, render_template, request
from flask_wtf.csrf import CSRFError
from markupsafe import Markup
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from hms.cli import register_cli
from hms.config import get_config
from hms.extensions import csrf, db, limiter, login_manager, migrate, talisman
from hms.filters import register_filters
from hms.logging import init_logging
from hms.models.user import User
from hms.routes.health import health_bp
from hms.services.appointments import InvalidStateTransitionError


def create_app(config_object=None):
    """Application factory for Hospital Management System (A-01)."""
    app = Flask(__name__, template_folder='templates', static_folder='static')

    if config_object:
        app.config.from_object(config_object)
    else:
        app.config.from_object(get_config())

    # Initialize Structured Logging & Sentry (R-01, R-07)
    init_logging(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Reverse proxy support (R-06)
    if app.config.get('BEHIND_PROXY', False):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1,
            x_port=1,
            x_prefix=1,
        )

    # Host header validation (R-06)
    allowed_hosts = app.config.get('ALLOWED_HOSTS')
    if allowed_hosts:
        @app.before_request
        def validate_host_header():
            host = request.host.split(':')[0]
            if host not in allowed_hosts and '*' not in allowed_hosts:
                abort(400, description="Untrusted Host header.")

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

        # Cache-Control: long-cache for static assets (R-06)
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            return response

        # Cache-Control: no-store on sensitive clinical & financial data (S-08)
        sensitive_prefixes = ('/bills', '/records', '/profile', '/admin', '/discharge', '/edit_record', '/add_record')
        if any(request.path.startswith(p) for p in sensitive_prefixes):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
        return response

    # Central Teardown Hook for Database Sessions (R-03)
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            db.session.rollback()
        db.session.remove()

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

    def is_json_request():
        return (
            request.is_json
            or request.path.startswith('/api/')
            or 'application/json' in request.headers.get('Accept', '')
        )

    # Custom Error Handlers (S-09, R-03)
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        req_id = getattr(g, 'request_id', None)
        if is_json_request():
            return jsonify({"error": "CSRF validation failed", "description": e.description, "request_id": req_id}), 400
        return render_template('errors/400.html', message=f"Security verification failed: {e.description}. Please refresh the page and try again.", request_id=req_id), 400

    @app.errorhandler(400)
    def handle_bad_request(e):
        req_id = getattr(g, 'request_id', None)
        if is_json_request():
            return jsonify({"error": "Bad Request", "description": getattr(e, 'description', str(e)), "request_id": req_id}), 400
        return render_template('errors/400.html', message=getattr(e, 'description', None), request_id=req_id), 400

    @app.errorhandler(InvalidStateTransitionError)
    def handle_invalid_transition(e):
        req_id = getattr(g, 'request_id', None)
        if is_json_request():
            return jsonify({"error": "Conflict", "description": str(e), "request_id": req_id}), 409
        return render_template('errors/409.html', message=f"State Conflict: {e}", request_id=req_id), 409

    @app.errorhandler(IntegrityError)
    def handle_db_integrity_error(e):
        db.session.rollback()
        req_id = getattr(g, 'request_id', None)
        app.logger.warning(f"Database IntegrityError intercepted: {e}")
        if is_json_request():
            return jsonify({"error": "Conflict", "description": "Database constraint violation (e.g. duplicate key or slot).", "request_id": req_id}), 409
        return render_template('errors/409.html', message="A conflict occurred: the requested record, identifier, or slot is already in use.", request_id=req_id), 409

    @app.errorhandler(OperationalError)
    def handle_db_operational_error(e):
        db.session.rollback()
        req_id = getattr(g, 'request_id', None)
        app.logger.error(f"Database OperationalError intercepted: {e}")
        if is_json_request():
            return jsonify({"error": "Service Unavailable", "description": "Database operation timed out or connection failed.", "request_id": req_id}), 503
        return render_template('errors/500.html', request_id=req_id), 503

    @app.errorhandler(SQLAlchemyError)
    def handle_general_sqlalchemy_error(e):
        db.session.rollback()
        req_id = getattr(g, 'request_id', None)
        app.logger.error(f"SQLAlchemyError intercepted: {e}")
        if is_json_request():
            return jsonify({"error": "Database Error", "request_id": req_id}), 500
        return render_template('errors/500.html', request_id=req_id), 500

    @app.errorhandler(403)
    def handle_forbidden(e):
        req_id = getattr(g, 'request_id', None)
        if is_json_request():
            return jsonify({"error": "Forbidden", "description": getattr(e, 'description', str(e)), "request_id": req_id}), 403
        return render_template('errors/403.html', message=getattr(e, 'description', None), request_id=req_id), 403

    @app.errorhandler(404)
    def handle_not_found(e):
        req_id = getattr(g, 'request_id', None)
        if is_json_request():
            return jsonify({"error": "Not Found", "description": getattr(e, 'description', str(e)), "request_id": req_id}), 404
        return render_template('errors/404.html', message=getattr(e, 'description', None), request_id=req_id), 404

    @app.errorhandler(429)
    def handle_rate_limit(e):
        req_id = getattr(g, 'request_id', None)
        if is_json_request():
            return jsonify({"error": "Rate limit exceeded", "description": getattr(e, 'description', str(e)), "request_id": req_id}), 429
        return render_template('errors/429.html', message=getattr(e, 'description', None), request_id=req_id), 429

    @app.errorhandler(500)
    def handle_server_error(e):
        req_id = getattr(g, 'request_id', None)
        if is_json_request():
            return jsonify({"error": "Internal Server Error", "request_id": req_id}), 500
        return render_template('errors/500.html', request_id=req_id), 500

    # Register custom Jinja filters (A-04)
    register_filters(app)

    # Register Blueprints
    from hms.routes.admin import admin_bp
    from hms.routes.api import api_bp
    from hms.routes.auth import auth_bp
    from hms.routes.doctor import doctor_bp
    from hms.routes.main import main_bp
    from hms.routes.patient import patient_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp)

    @app.route('/api/docs')
    def redirect_api_docs():
        from flask import redirect
        return redirect('/api/v1/docs')

    # Register CLI
    register_cli(app)

    return app
