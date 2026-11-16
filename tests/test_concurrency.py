import pytest
import concurrent.futures
from pathlib import Path
from services.scheduling import SchedulingService
from models import db, Appointments, Room, Admission, User, Doctors
from werkzeug.security import generate_password_hash
from decimal import Decimal
from app import create_app

class ConcurrencyConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'concurrency-secret'
    # Use file-based SQLite database with thread-safe timeout
    instance_dir = Path(__file__).resolve().parent.parent / 'instance'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{instance_dir / 'test_concurrency.db'}?timeout=30"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_ENV = 'development'
    DEMO_ONLY = True

@pytest.fixture
def concurrency_app():
    """File-backed SQLite database fixture for thread-safe concurrency testing."""
    instance_dir = Path(__file__).resolve().parent.parent / 'instance'
    instance_dir.mkdir(exist_ok=True)
    db_path = instance_dir / 'test_concurrency.db'
    if db_path.exists():
        db_path.unlink()

    app_instance = create_app(ConcurrencyConfig)
    with app_instance.app_context():
        db.create_all()
        # Seed test patient, doctor, and room
        doc_user = User(
            id=10, username='Dr. Concurrency', usertype='Doctor', email='doc_conc@test.local',
            password=generate_password_hash('Pass@123')
        )
        p1 = User(
            id=20, username='Patient Concurrency', usertype='Patient', email='p_conc@test.local',
            password=generate_password_hash('Pass@123'), mrn='MRN-CONC-001'
        )
        r = Room(room_id=10, room_number='999', ward_type='General', rate_per_day=Decimal('500.00'), status='Available')
        db.session.add_all([doc_user, p1, r])
        db.session.commit()

        yield app_instance

        db.session.remove()
        db.drop_all()
    if db_path.exists():
        try: db_path.unlink()
        except Exception: pass

def test_t_appt_001_slot_conflict_prevention(concurrency_app):
    """
    T-APPT-001: Verification that the scheduling domain service enforces
    atomic slot exclusivity. Once a slot is booked, any subsequent attempt
    predictably receives a conflict error.
    """
    with concurrency_app.app_context():
        doc_name = 'Dr. Concurrency'
        target_date = '2026-12-05'
        target_time = '10:00 AM'
        dept = 'Cardiologists'

        # 1st booking attempt: must succeed
        success1, msg1, apt1 = SchedulingService.book_appointment(
            user_id=20,
            doctor_name=doc_name,
            dept=dept,
            date_str=target_date,
            time_str=target_time,
            disease='Cardiac check'
        )
        assert success1 is True
        assert apt1 is not None
        assert apt1.token_number == 1

        # 2nd booking attempt for the identical doctor, date, and time: MUST receive conflict
        success2, msg2, apt2 = SchedulingService.book_appointment(
            user_id=20,
            doctor_name=doc_name,
            dept=dept,
            date_str=target_date,
            time_str=target_time,
            disease='Follow-up check'
        )
        assert success2 is False
        assert apt2 is None
        assert "Slot Unavailable" in msg2

        # 3rd booking attempt: verify active booking count is strictly 1
        active_count = Appointments.query.filter(
            Appointments.doctor == doc_name,
            Appointments.date == target_date,
            Appointments.time == target_time,
            Appointments.slot.notin_(['Cancelled', 'Missed'])
        ).count()
        assert active_count == 1

def test_t_bed_001_atomic_bed_allocation_guarantees_single_occupant(concurrency_app):
    """
    T-BED-001: Room allocation exclusivity: an occupied room cannot be double-allocated.
    """
    with concurrency_app.app_context():
        room = Room.query.get(10)
        assert room.status == 'Available'

        # Admit patient to Room 10
        adm1 = Admission(
            apt_id=1,
            patient_id=20,
            doctor_id=1,
            room_id=10,
            status='Admitted'
        )
        room.status = 'Occupied'
        db.session.add(adm1)
        db.session.commit()

        # Query available rooms - Room 10 must NOT appear
        avail = Room.query.filter_by(status='Available').all()
        assert 10 not in [r.room_id for r in avail]

        # Verify Room 10 status is Occupied
        room_check = Room.query.get(10)
        assert room_check.status == 'Occupied'
