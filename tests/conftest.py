import pytest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date

# Add PROJECT directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'PROJECT'))

from app import create_app
from config import TestingConfig
from models import db, User, Doctors, Appointments, MedicalRecord, Billing, Room, Admission
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    """Create a clean in-memory Flask application for characterization tests."""
    app_instance = create_app(TestingConfig)
    with app_instance.app_context():
        db.create_all()
        _seed_fixtures()
        yield app_instance
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def _seed_fixtures():
    """Seed test fixtures with isolated roles."""
    admin = User(
        id=1, username='Administrator', usertype='Admin', email='admin@test.local',
        password=generate_password_hash('AdminPass@123'), phone='555-0100', gender='Male'
    )
    doc1_user = User(
        id=2, username='Dr. Sharma', usertype='Doctor', email='doc1@test.local',
        password=generate_password_hash('DoctorPass@123'), phone='555-0101', gender='Male'
    )
    doc2_user = User(
        id=3, username='Dr. Patel', usertype='Doctor', email='doc2@test.local',
        password=generate_password_hash('DoctorPass@123'), phone='555-0102', gender='Female'
    )
    p1 = User(
        id=4, username='Patient One', usertype='Patient', email='p1@test.local',
        password=generate_password_hash('PatientPass@123'), phone='555-0201', gender='Male'
    )
    p2 = User(
        id=5, username='Patient Two', usertype='Patient', email='p2@test.local',
        password=generate_password_hash('PatientPass@123'), phone='555-0202', gender='Female'
    )
    db.session.add_all([admin, doc1_user, doc2_user, p1, p2])
    db.session.flush()

    d1 = Doctors(did=1, user_id=doc1_user.id, dept='Cardiologists')
    d2 = Doctors(did=2, user_id=doc2_user.id, dept='Dermatologists')
    db.session.add_all([d1, d2])

    r1 = Room(room_id=1, room_number='101', ward_type='General', rate_per_day=800.00, status='Available')
    r2 = Room(room_id=2, room_number='201', ward_type='ICU', rate_per_day=3500.00, status='Available')
    db.session.add_all([r1, r2])

    today_str = str(date.today())
    apt1 = Appointments(
        apt_id=1, user_id=p1.id, doctor='Dr. Sharma', dept='Cardiologists',
        date=today_str, time='10:00 AM', disease='Hypertension', slot='Scheduled'
    )
    db.session.add(apt1)
    db.session.commit()
