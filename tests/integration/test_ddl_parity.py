import os

import pytest
from sqlalchemy import create_engine, inspect

from hms.models import db

MYSQL_URL = os.environ.get(
    'INTEGRATION_DATABASE_URL',
    'mysql+pymysql://hms_user:TestPassword%40123@127.0.0.1:3306/hms_test'
)

from sqlalchemy.exc import DatabaseError, OperationalError


def is_mysql_available():
    try:
        engine = create_engine(MYSQL_URL)
        with engine.connect() as conn:
            conn.execute(db.text("SELECT 1"))
        return True
    except (OperationalError, DatabaseError):
        return False

@pytest.mark.skipif(not is_mysql_available(), reason="Native MySQL 8/9 is not available")
def test_d12_model_ddl_parity(app):
    """
    D-12: Parity test between SQLAlchemy metadata and the migrated MySQL database.
    Ensures that ORM models and database tables do not drift in columns, names, or types.
    """
    engine = create_engine(MYSQL_URL)
    inspector = inspect(engine)

    db_tables = set(inspector.get_table_names())
    orm_tables = set(db.metadata.tables.keys())

    # 1. Assert all ORM tables are present in the migrated MySQL database
    for table_name in orm_tables:
        assert table_name in db_tables, f"ORM table '{table_name}' is missing in the migrated database."

    # 2. Check column parity for key tables
    for table_name, table in db.metadata.tables.items():
        db_cols = {col['name']: col for col in inspector.get_columns(table_name)}
        for orm_col in table.columns:
            assert orm_col.name in db_cols, (
                f"Column '{orm_col.name}' in table '{table_name}' missing from database schema."
            )

    # 3. Explicit D-12 regression assertions (resolves legacy disparities)
    apt_cols = {c['name']: str(c['type']) for c in inspector.get_columns('appointments')}
    assert 'DATETIME' in apt_cols['starts_at'].upper()
    assert 'active_slot_key' in apt_cols

    user_cols = {c['name']: str(c['type']) for c in inspector.get_columns('user')}
    assert 'VARCHAR' in user_cols['usertype'].upper()
    assert 'VARCHAR' in user_cols['email'].upper()

    invoice_cols = {c['name']: str(c['type']) for c in inspector.get_columns('invoice')}
    assert any(num_type in invoice_cols['total'].upper() for num_type in ['DECIMAL', 'NUMERIC'])
