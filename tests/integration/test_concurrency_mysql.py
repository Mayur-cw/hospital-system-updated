import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pytest
from sqlalchemy import create_engine

from hms import create_app
from hms.config import Config
from hms.models import Appointment, Department, Doctor, User, db
from hms.services.appointments import (
    AppointmentError,
    AppointmentService,
    SlotAlreadyBookedError,
)

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

class MySQLIntegrationConfig(Config):
    TESTING = True
    FLASK_DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = MYSQL_URL

@pytest.mark.skipif(not is_mysql_available(), reason="Native MySQL is not available")
def test_t03_parallel_slot_booking_concurrency():
    """
    T-03 / D-03: Concurrency test on real MySQL database.
    20 parallel booking requests competing for the exact same slot.
    Asserts: Exactly 1 succeeds, 19 fail with SlotAlreadyBookedError, exactly 1 row in DB.
    """
    app = create_app(MySQLIntegrationConfig)

    with app.app_context():
        # Ensure test entities exist
        dept = Department.query.filter_by(code='CARD').first()
        if not dept:
            dept = Department(name='Cardiology', code='CARD')
            db.session.add(dept)
            db.session.commit()

        doc_user = User.query.filter_by(email='dr.concurrent@hms.local').first()
        if not doc_user:
            doc_user = User(
                username='Dr. Concurrent', email='dr.concurrent@hms.local',
                password='pwd', usertype='Doctor'
            )
            db.session.add(doc_user)
            db.session.flush()
            doc = Doctor(user_id=doc_user.id, department_id=dept.id)
            db.session.add(doc)
            db.session.commit()
        else:
            doc = Doctor.query.filter_by(user_id=doc_user.id).first()

        doc_id = doc.id

        # Target competing slot
        target_slot = datetime(2027, 5, 10, 11, 0)
        # Clear any preexisting appointment at this slot
        Appointment.query.filter_by(doctor_id=doc_id, starts_at=target_slot).delete()
        db.session.commit()

    # Function executed concurrently across worker threads
    def book_worker(worker_id):
        # Each thread gets its own app context and session
        with app.app_context():
            # Seed unique patient for this worker if not present
            p_email = f"patient_{worker_id}@concurrent.local"
            p = User.query.filter_by(email=p_email).first()
            if not p:
                p = User(username=f"Patient {worker_id}", email=p_email, password='pwd', usertype='Patient')
                db.session.add(p)
                db.session.commit()

            try:
                apt = AppointmentService.book(
                    patient_id=p.id,
                    doctor_id=doc_id,
                    starts_at=target_slot,
                    reason=f"Worker {worker_id} request"
                )
                return ('SUCCESS', worker_id, apt.id)
            except SlotAlreadyBookedError:
                return ('REJECTED_SLOT_TAKEN', worker_id, None)
            except (AppointmentError, OperationalError, DatabaseError) as e:
                return ('ERROR', worker_id, str(e))

    num_threads = 20
    results = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(book_worker, i) for i in range(num_threads)]
        for f in as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r[0] == 'SUCCESS']
    rejections = [r for r in results if r[0] == 'REJECTED_SLOT_TAKEN']
    errors = [r for r in results if r[0] == 'ERROR']

    print(f"\nConcurrency Results: {len(successes)} Success, {len(rejections)} Rejected, {len(errors)} Errors")
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {successes}"
    assert len(rejections) == num_threads - 1
    assert len(errors) == 0

    with app.app_context():
        final_count = Appointment.query.filter_by(doctor_id=doc_id, starts_at=target_slot).count()
        assert final_count == 1
