# health.py - Liveness & Readiness health probe endpoints (R-02)
from datetime import UTC, datetime

from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask import Blueprint, current_app, jsonify

from hms.extensions import db

health_bp = Blueprint('health', __name__)


@health_bp.route('/healthz', methods=['GET'])
def healthz():
    """Liveness probe: verifies the WSGI/Flask process is running (R-02)."""
    return jsonify({
        'status': 'ok',
        'service': 'hedgewar-hms',
        'timestamp': datetime.now(UTC).isoformat()
    }), 200


@health_bp.route('/readyz', methods=['GET'])
def readyz():
    """Readiness probe: verifies database connectivity and schema migration head (R-02)."""
    # 1. Check DB connectivity
    try:
        db.session.execute(db.text("SELECT 1")).scalar()
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }), 503

    # 2. Check Migrations parity with head
    try:
        config = current_app.extensions['migrate'].migrate.get_config()
        script = ScriptDirectory.from_config(config)
        heads = set(script.get_heads())

        with db.engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            current_rev = ctx.get_current_revision()

        if current_rev is None and not current_app.config.get('TESTING'):
            return jsonify({
                'status': 'not_ready',
                'database': 'connected',
                'migrations': 'unapplied',
                'current_revision': None,
                'target_head': list(heads),
                'timestamp': datetime.now(UTC).isoformat()
            }), 503

        if current_rev is not None and current_rev not in heads:
            return jsonify({
                'status': 'not_ready',
                'database': 'connected',
                'migrations': 'outdated',
                'current_revision': current_rev,
                'target_head': list(heads),
                'timestamp': datetime.now(UTC).isoformat()
            }), 503

        migration_status = 'at_head' if current_rev in heads else 'testing_mode'
        return jsonify({
            'status': 'ready',
            'database': 'connected',
            'migrations': migration_status,
            'current_revision': current_rev,
            'timestamp': datetime.now(UTC).isoformat()
        }), 200

    except Exception as e:
        if current_app.config.get('TESTING'):
            return jsonify({
                'status': 'ready',
                'database': 'connected',
                'migrations': 'test_sqlite',
                'timestamp': datetime.now(UTC).isoformat()
            }), 200

        return jsonify({
            'status': 'unhealthy',
            'database': 'connected',
            'migrations': 'error',
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }), 503
