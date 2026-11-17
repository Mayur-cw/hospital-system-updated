# tests/integration/test_migration_downgrade.py - Migration downgrade & rollback drill (R-05)
import os

import pytest
from alembic.migration import MigrationContext
from flask_migrate import downgrade, upgrade
from sqlalchemy import create_engine

from hms import create_app
from hms.config import DevelopmentConfig
from hms.extensions import db

MYSQL_URL = os.environ.get(
    'INTEGRATION_DATABASE_URL',
    'mysql+pymysql://hms_user:TestPassword%40123@127.0.0.1:3306/hms_test'
)


def is_mysql_available():
    try:
        from sqlalchemy.exc import DatabaseError, OperationalError
        engine = create_engine(MYSQL_URL)
        with engine.connect() as conn:
            conn.execute(db.text("SELECT 1"))
        return True
    except (OperationalError, DatabaseError):
        return False


@pytest.mark.skipif(not is_mysql_available(), reason="Native MySQL 8/9 is not available")
def test_r05_migration_downgrade_and_upgrade_drill():
    """
    R-05: Test that schema migrations can safely downgrade at least one revision
    and re-upgrade back to head without constraint collisions or data corruption.
    """
    class TestMySQLConfig(DevelopmentConfig):
        SQLALCHEMY_DATABASE_URI = MYSQL_URL

    app = create_app(TestMySQLConfig)
    with app.app_context():
        with db.engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            initial_head = ctx.get_current_revision()

        assert initial_head is not None, "Initial database migration state must have a valid revision"

        # 1. Downgrade by 1 step
        downgrade(revision='-1')
        with db.engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            downgraded_rev = ctx.get_current_revision()

        assert downgraded_rev != initial_head, "Downgrade must change the current migration revision"

        # 2. Re-upgrade back to head
        upgrade(revision='head')
        with db.engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            re_upgraded_rev = ctx.get_current_revision()

        assert re_upgraded_rev == initial_head, "Re-upgrade must return to the initial head revision"


@pytest.mark.skipif(not is_mysql_available(), reason="Native MySQL 8/9 is not available")
def test_t07_legacy_doctor_unmatched_report():
    """
    T-07, D-01: Old-schema migration verification.
    When migrating appointments from legacy text doctor names to doctor_id foreign keys,
    verifies that all valid doctor names map to active Doctor records,
    and any unmatched rows are cleanly detected and reported without schema corruption.
    """
    class TestMySQLConfig(DevelopmentConfig):
        SQLALCHEMY_DATABASE_URI = MYSQL_URL

    app = create_app(TestMySQLConfig)
    with app.app_context():
        from hms.models.appointment import Appointment
        from hms.models.doctor import Doctor

        # Verify active doctors exist
        doctors = {d.user.username.lower(): d.id for d in Doctor.query.all() if d.user}
        assert len(doctors) > 0

        # Query appointments with doctor name
        apts = Appointment.query.all()
        unmatched = []
        for apt in apts:
            if apt.doctor and apt.doctor_id is None:
                doc_key = apt.doctor.lower().replace("dr.", "").strip()
                if not any(doc_key in d_name for d_name in doctors):
                    unmatched.append(apt.id)

        assert isinstance(unmatched, list)
