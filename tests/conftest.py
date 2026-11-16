import pytest
import os
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, date, timedelta

# Ensure PROJECT directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'PROJECT'))

from app import create_app
from models import db, User, Doctors, Appointments, MedicalRecord, Billing, Room, Admission, AuditLog
from werkzeug.security import generate_password_hash

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = True
    SECRET_KEY = 'test-secret-key-champion-suite'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_ENV = 'development'
    DEMO_ONLY = True

class TestConfigNoCSRF(TestConfig):
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    """Create a clean in-memory Flask application for tests."""
    app_instance = create_app(TestConfig)
    with app_instance.app_context():
        db.create_all()
        # Seed test fixtures
        _seed_test_data()
        yield app_instance
        db.session.remove()
        db.drop_all()

@pytest.fixture
def app_no_csrf():
    """App instance with CSRF disabled for functional workflow tests."""
    app_instance = create_app(TestConfigNoCSRF)
    with app_instance.app_context():
        db.create_all()
        _seed_test_data()
        yield app_instance
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def client_no_csrf(app_no_csrf):
    return app_no_csrf.test_client()

def _seed_test_data():
    """Seed test fixtures with isolated roles."""
    admin = User(
        id=1, username='Admin User', usertype='Admin', email='admin@test.local',
        password=generate_password_hash('Pass@123'), phone='555-1001', gender='Male'
    )
    doc1_user = User(
        id=2, username='Dr. First', usertype='Doctor', email='doc1@test.local',
        password=generate_password_hash('Pass@123'), phone='555-1002', gender='Male'
    )
    doc2_user = User(
        id=3, username='Dr. Second', usertype='Doctor', email='doc2@test.local',
        password=generate_password_hash('Pass@123'), phone='555-1003', gender='Female'
    )
    p1 = User(
        id=4, username='Patient One', usertype='Patient', email='p1@test.local',
        password=generate_password_hash('Pass@123'), phone='555-2001', gender='Male',
        mrn='MRN-2026-0001', allergies='Penicillin'
    )
    p2 = User(
        id=5, username='Patient Two', usertype='Patient', email='p2@test.local',
        password=generate_password_hash('Pass@123'), phone='555-2002', gender='Female',
        mrn='MRN-2026-0002', allergies='None known'
    )
    cashier = User(
        id=6, username='Cashier User', usertype='Cashier', email='cashier@test.local',
        password=generate_password_hash('Pass@123'), phone='555-3001', gender='Male'
    )
    receptionist = User(
        id=7, username='Receptionist User', usertype='Receptionist', email='reception@test.local',
        password=generate_password_hash('Pass@123'), phone='555-3002', gender='Female'
    )
    db.session.add_all([admin, doc1_user, doc2_user, p1, p2, cashier, receptionist])
    db.session.flush()

    # Doctors profiles
    d1 = Doctors(did=1, user_id=doc1_user.id, dept='Cardiologists')
    d2 = Doctors(did=2, user_id=doc2_user.id, dept='Dermatologists')
    db.session.add_all([d1, d2])

    # Rooms
    r1 = Room(room_id=1, room_number='101', ward_type='General', rate_per_day=Decimal('800.00'), status='Available')
    r2 = Room(room_id=2, room_number='201', ward_type='ICU', rate_per_day=Decimal('3500.00'), status='Available')
    db.session.add_all([r1, r2])

    # Appointments
    today_str = date.today().isoformat()
    apt1 = Appointments(
        apt_id=1, user_id=p1.id, doctor='Dr. First', dept='Cardiologists',
        date=today_str, time='10:00 AM', disease='Hypertension', slot='Scheduled', token_number=1
    )
    apt2 = Appointments(
        apt_id=2, user_id=p2.id, doctor='Dr. Second', dept='Dermatologists',
        date=today_str, time='11:00 AM', disease='Eczema', slot='Scheduled', token_number=1
    )
    db.session.add_all([apt1, apt2])
    db.session.flush()

    # Billing
    b1 = Billing(bill_id=1, apt_id=apt1.apt_id, user_id=p1.id, amount=Decimal('500.00'), status='Unpaid')
    b2 = Billing(bill_id=2, apt_id=apt2.apt_id, user_id=p2.id, amount=Decimal('500.00'), status='Unpaid')
    db.session.add_all([b1, b2])

    db.session.commit()
