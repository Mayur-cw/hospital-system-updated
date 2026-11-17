import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import DatabaseError, OperationalError

from hms import create_app
from hms.config import Config
from hms.models import (
    Admission,
    AdmissionStatus,
    Appointment,
    Department,
    Doctor,
    Invoice,
    Payment,
    Room,
    RoomStatus,
    User,
    db,
)
from hms.services.admissions import AdmissionService, RoomNotAvailableError
from hms.services.appointments import (
    AppointmentError,
    AppointmentService,
    SlotAlreadyBookedError,
)
from hms.services.billing import BillingService

MYSQL_URL = os.environ.get(
    'INTEGRATION_DATABASE_URL',
    'mysql+pymysql://hms_user:TestPassword%40123@127.0.0.1:3306/hms_test'
)


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


@pytest.mark.skipif(not is_mysql_available(), reason="Native MySQL is not available")
def test_t03_double_submitted_discharge_concurrency():
    """
    T-03: Double-submitted discharge -> exactly one invoice created.
    Simulates user double-clicking 'Discharge' or two admins discharging simultaneously.
    """
    app = create_app(MySQLIntegrationConfig)

    with app.app_context():
        # Setup doctor, patient, room, admission
        doc = Doctor.query.first()
        patient = User.query.filter_by(usertype="Patient").first()
        room = Room.query.filter_by(room_number="ICU-CONCUR").first()
        if not room:
            room = Room(room_number="ICU-CONCUR", ward_type="ICU", rate_per_day=Decimal("3000.00"), status=RoomStatus.AVAILABLE)
            db.session.add(room)
            db.session.commit()
        else:
            room.status = RoomStatus.AVAILABLE
            db.session.commit()

        # Admit patient
        admission = AdmissionService.admit(patient.id, doc.id, room.id, tentative_days=3)
        admission_id = admission.id

    def discharge_worker(worker_id):
        with app.app_context():
            try:
                res = AdmissionService.discharge(admission_id)
                return ('SUCCESS', worker_id, res.id)
            except Exception as e:
                return ('ERROR', worker_id, str(e))

    num_threads = 2
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(discharge_worker, i) for i in range(num_threads)]
        for f in as_completed(futures):
            f.result()

    # Both workers finish cleanly because of row-level lock and idempotency guard
    with app.app_context():
        invoices = Invoice.query.filter_by(admission_id=admission_id).all()
        assert len(invoices) == 1, f"Expected exactly 1 invoice for admission, got {len(invoices)}"
        final_adm = db.session.get(Admission, admission_id)
        assert final_adm.status == AdmissionStatus.DISCHARGED
        final_room = db.session.get(Room, room.id)
        assert final_room.status == RoomStatus.AVAILABLE


@pytest.mark.skipif(not is_mysql_available(), reason="Native MySQL is not available")
def test_t03_parallel_room_admission_concurrency():
    """
    T-03: Two admissions into one room -> exactly one succeeds.
    """
    app = create_app(MySQLIntegrationConfig)

    with app.app_context():
        doc = Doctor.query.first()
        p1 = User.query.filter_by(email="p1.admit@concurrent.local").first()
        if not p1:
            p1 = User(username="P1 Admit", email="p1.admit@concurrent.local", password="pwd", usertype="Patient")
            db.session.add(p1)
        p2 = User.query.filter_by(email="p2.admit@concurrent.local").first()
        if not p2:
            p2 = User(username="P2 Admit", email="p2.admit@concurrent.local", password="pwd", usertype="Patient")
            db.session.add(p2)

        room = Room.query.filter_by(room_number="RM-SINGLE-OCC").first()
        if not room:
            room = Room(room_number="RM-SINGLE-OCC", ward_type="Private", rate_per_day=Decimal("2000.00"), status=RoomStatus.AVAILABLE)
            db.session.add(room)
        else:
            room.status = RoomStatus.AVAILABLE
            Admission.query.filter_by(room_id=room.id, status=AdmissionStatus.ADMITTED).delete()
        db.session.commit()

        room_id = room.id
        doc_id = doc.id
        p1_id = p1.id
        p2_id = p2.id

    def admit_worker(patient_id):
        with app.app_context():
            try:
                adm = AdmissionService.admit(patient_id, doc_id, room_id, tentative_days=2)
                return ('SUCCESS', patient_id, adm.id)
            except RoomNotAvailableError:
                return ('REJECTED_OCCUPIED', patient_id, None)
            except Exception as e:
                return ('ERROR', patient_id, str(e))

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(admit_worker, p1_id)
        f2 = executor.submit(admit_worker, p2_id)
        results = [f1.result(), f2.result()]

    successes = [r for r in results if r[0] == 'SUCCESS']
    rejections = [r for r in results if r[0] == 'REJECTED_OCCUPIED']

    assert len(successes) == 1, f"Expected 1 admission to succeed, got {len(successes)}"
    assert len(rejections) == 1, f"Expected 1 admission to be rejected, got {len(rejections)}"

    with app.app_context():
        active_admissions = Admission.query.filter_by(room_id=room_id, status=AdmissionStatus.ADMITTED).count()
        assert active_admissions == 1


@pytest.mark.skipif(not is_mysql_available(), reason="Native MySQL is not available")
def test_t03_duplicate_payment_webhook_idempotency_concurrency():
    """
    T-03: Duplicate payment webhook -> exactly one payment recorded.
    10 parallel webhook calls with identical idempotency_key.
    """
    app = create_app(MySQLIntegrationConfig)

    with app.app_context():
        patient = User.query.filter_by(usertype="Patient").first()
        invoice = Invoice(
            invoice_number=f"INV-IDEMP-{datetime.now().strftime('%M%S%f')}",
            patient_id=patient.id,
            subtotal=Decimal("1500.00"),
            tax=Decimal("0.00"),
            discount=Decimal("0.00"),
            total=Decimal("1500.00"),
        )
        db.session.add(invoice)
        db.session.commit()
        invoice_id = invoice.id

    idemp_key = f"webhook-evt-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    def payment_worker(worker_id):
        with app.app_context():
            try:
                pmt = BillingService.record_payment(
                    invoice_id=invoice_id,
                    amount=Decimal("1500.00"),
                    idempotency_key=idemp_key,
                    gateway_ref="gw_ref_test"
                )
                return ('SUCCESS', worker_id, pmt.id)
            except Exception as e:
                return ('ERROR', worker_id, str(e))

    num_threads = 10
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(payment_worker, i) for i in range(num_threads)]
        results = [f.result() for f in as_completed(futures)]

    # All workers return successfully (either creating or fetching existing payment)
    for r in results:
        assert r[0] == 'SUCCESS', f"Worker returned unexpected state: {r}"

    with app.app_context():
        payments = Payment.query.filter_by(idempotency_key=idemp_key).all()
        assert len(payments) == 1, f"Expected exactly 1 payment record, found {len(payments)}"
        inv = db.session.get(Invoice, invoice_id)
        assert inv.status == "Paid"

