# logging.py - Structured JSON logging & PHI scrubbing (R-01, R-07)
import json
import logging
import re
import sys
import time
from datetime import UTC, datetime
from typing import Any, Dict

from flask import g, has_app_context, has_request_context, request
from flask_login import current_user

SENSITIVE_KEYS = {
    'password',
    'secret',
    'token',
    'csrf_token',
    'access_token',
    'refresh_token',
    'api_key',
    'credit_card',
    'cvv',
    'diagnosis',
    'symptoms',
    'prescription',
    'allergies',
    'chronic_conditions',
    'notes',
}

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
CREDENTIAL_REGEX = re.compile(r'(?i)\b(password|secret|token|api_key)\s*[:=]\s*\S+')


def scrub_phi(data: Any) -> Any:
    """Scrub Personally Identifiable Information (PII) and Protected Health Information (PHI)."""
    if isinstance(data, dict):
        scrubbed = {}
        for k, v in data.items():
            if any(sens in k.lower() for sens in SENSITIVE_KEYS):
                scrubbed[k] = '[REDACTED]'
            else:
                scrubbed[k] = scrub_phi(v)
        return scrubbed
    elif isinstance(data, (list, tuple)):
        return [scrub_phi(item) for item in data]
    elif isinstance(data, str):
        # Mask credentials, emails, and phone numbers in raw string logs
        val = CREDENTIAL_REGEX.sub(r'\1=[REDACTED]', data)
        val = EMAIL_REGEX.sub('[EMAIL_REDACTED]', val)
        val = PHONE_REGEX.sub('[PHONE_REDACTED]', val)
        return val
    return data


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON without exposing PHI (R-01)."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': scrub_phi(record.getMessage()),
        }

        # Context-aware request tracing
        if has_request_context():
            log_entry['request_id'] = getattr(g, 'request_id', None)
            log_entry['method'] = request.method
            log_entry['path'] = request.path
            log_entry['endpoint'] = request.endpoint
            log_entry['ip'] = request.remote_addr

            # Log actor identifier safely (Numeric User ID ONLY, NEVER name/email)
            if has_app_context() and current_user and getattr(current_user, 'is_authenticated', False):
                log_entry['user_id'] = current_user.id
                log_entry['user_role'] = getattr(current_user, 'usertype', None)
            else:
                log_entry['user_id'] = None

        if record.exc_info:
            log_entry['exception'] = scrub_phi(self.formatException(record.exc_info))

        return json.dumps(log_entry, default=str)


def init_logging(app):
    """Configure structured JSON logging and optional Sentry monitoring (R-01, R-07)."""
    # Replace default handler with JSONFormatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    log_level = app.config.get('LOG_LEVEL', 'INFO')
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    app.logger.propagate = False

    # Root logger formatting for consistency across libraries
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.WARNING)

    # Request lifecycle timing & structured request logger
    @app.before_request
    def record_start_time():
        g.start_time = time.monotonic()

    @app.after_request
    def log_request_summary(response):
        # Ignore noisy static file hits
        if request.path.startswith('/static/'):
            return response

        start_time = getattr(g, 'start_time', None)
        latency_ms = round((time.monotonic() - start_time) * 1000, 2) if start_time else 0.0

        user_id = None
        if current_user and getattr(current_user, 'is_authenticated', False):
            user_id = current_user.id

        log_payload = {
            'timestamp': datetime.now(UTC).isoformat(),
            'event': 'http_request',
            'request_id': getattr(g, 'request_id', None),
            'user_id': user_id,
            'method': request.method,
            'path': request.path,
            'endpoint': request.endpoint,
            'status': response.status_code,
            'latency_ms': latency_ms,
            'ip': request.remote_addr,
        }

        # Log at INFO for normal requests, WARNING for 4xx, ERROR for 5xx
        if response.status_code >= 500:
            app.logger.error(json.dumps(log_payload))
        elif response.status_code >= 400:
            app.logger.warning(json.dumps(log_payload))
        else:
            app.logger.info(json.dumps(log_payload))

        return response

    # Optional Sentry initialization with PHI scrubbing (R-07)
    sentry_dsn = app.config.get('SENTRY_DSN')
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            def before_send(event, hint):
                return scrub_phi(event)

            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration(), SqlalchemyIntegration()],
                traces_sample_rate=app.config.get('SENTRY_TRACES_SAMPLE_RATE', 0.1),
                before_send=before_send,
                send_default_pii=False,
            )
            app.logger.info(json.dumps({"event": "sentry_initialized", "status": "active"}))
        except ImportError:
            app.logger.warning(json.dumps({
                "event": "sentry_missing",
                "message": "SENTRY_DSN configured but sentry-sdk is not installed."
            }))
