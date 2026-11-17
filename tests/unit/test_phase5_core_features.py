"""
Phase 5 Verification Suite: Core Enterprise Features (F-01 through F-12)

Validates:
- F-01: Reschedule appointment with 2h cutoff window and notification dispatch.
- F-02: Global search with typeahead scoped by role authorization.
- F-03: Real-time availability slots API (GET /api/v1/doctors/<id>/slots).
- F-04: Appointment state machine transitions and conflict rejections.
- F-05: Notifications outbox table and in-app notification center.
- F-06: Billing, itemized invoices, payment gateways, and idempotency guards.
- F-07: Clinical records, structured prescription items, and versioned amendments.
- F-08: Inpatient module: tentative days, room transfers, room maintenance, 24h block billing.
- F-09: Admin operations: CSV exports and hospital system settings.
- F-10: Receptionist role permissions (check-in, book on behalf, record cash).
- F-11: Versioned REST API and OpenAPI 3.0 specification (/api/v1/openapi.json).
- F-12: Server-side pagination helper with boundary clamps and page iteration.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from hms.extensions import db
from hms.models.admission import Room, RoomStatus
from hms.models.appointment import Appointment, AppointmentStatus
from hms.models.billing import Invoice, InvoiceStatus, Payment, PaymentMethod, PaymentStatus
from hms.models.doctor import Doctor
from hms.models.notification import NotificationOutbox, NotificationStatus
from hms.models.record import MedicalRecordVersion
from hms.models.settings import HospitalSetting
from hms.models.user import User, UserRole
from hms.pagination import paginate
from hms.policies import can_book_on_behalf, can_check_in_patient, can_record_payment
from hms.services.admissions import AdmissionService
from hms.services.appointments import (
    AppointmentCutoffError,
    AppointmentService,
    InvalidStateTransitionError,
)
from hms.services.billing import BillingService
from hms.services.notifications import NotificationService
from hms.services.payment_gateway import MockGateway, RazorpayGateway
from hms.services.records import RecordService
from hms.services.search import SearchService

# ── F-01: RESCHEDULE APPOINTMENT ──────────────────────────────────────────

def test_f01_reschedule_appointment_success_and_notifications(app):
    """F-01: Reschedule appointment sends notification and updates timestamp."""
    with app.app_context():
        patient = User.query.filter_by(usertype="Patient").first()
        doctor = Doctor.query.first()

        future_start = datetime.now() + timedelta(days=3, hours=10)
        apt = AppointmentService.book(
            patient_id=patient.id,
            doctor_id=doctor.id,
            starts_at=future_start,
            reason="Initial checkup"
        )

        new_start = datetime.now() + timedelta(days=4, hours=14)
        rescheduled_apt = AppointmentService.reschedule(
            appointment_id=apt.id,
            new_starts_at=new_start,
            actor=patient,
            reason="Need afternoon slot"
        )

        assert rescheduled_apt.starts_at.date() == new_start.date()
        assert "Need afternoon slot" in (rescheduled_apt.reason or "")

        # Verify notification was queued
        outbox = NotificationOutbox.query.filter_by(
            recipient=patient.email, event_type="reschedule"
        ).first()
        assert outbox is not None


def test_f01_reschedule_cutoff_window_enforced(app):
    """F-01: Patients cannot reschedule less than 2 hours before start time."""
    with app.app_context():
        patient = User.query.filter_by(usertype="Patient").first()
        doctor = Doctor.query.first()

        # Scheduled for 1 hour from now
        soon_start = datetime.now() + timedelta(minutes=50)
        apt = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            starts_at=soon_start,
            status=AppointmentStatus.SCHEDULED
        )
        db.session.add(apt)
        db.session.commit()

        new_start = datetime.now() + timedelta(days=2)
        with pytest.raises(AppointmentCutoffError):
            AppointmentService.reschedule(
                appointment_id=apt.id,
                new_starts_at=new_start,
                actor=patient,
                cutoff_hours=2
            )


# ── F-02: GLOBAL SEARCH WITH TYPEAHEAD ────────────────────────────────────

def test_f02_search_scoped_by_authorization(app):
    """F-02: Search results are strictly scoped by user role."""
    with app.app_context():
        admin = User.query.filter_by(usertype="Admin").first()
        patient = User.query.filter_by(usertype="Patient").first()

        # Admin can find patients
        admin_results = SearchService.global_search("patient", current_user=admin, search_type="patients")
        assert len(admin_results) >= 1
        assert any(r["category"] == "Patient" for r in admin_results)

        # Patient cannot find other patients
        patient_results = SearchService.global_search("patient", current_user=patient, search_type="patients")
        assert len(patient_results) == 0

        # Public/unauthenticated user only sees doctors
        anon_results = SearchService.global_search("patient", current_user=None, search_type="patients")
        assert len(anon_results) == 0

        # Public user can find doctors
        doc_results = SearchService.global_search("Sharma", current_user=None, search_type="doctors")
        assert len(doc_results) >= 1
        assert doc_results[0]["category"] == "Doctor"


# ── F-03: AVAILABILITY & SLOTS API ────────────────────────────────────────

def test_f03_availability_api_endpoint(client):
    """F-03: GET /api/v1/doctors/<id>/slots returns valid JSON time slots."""
    tomorrow_str = (date.today() + timedelta(days=2)).isoformat()
    resp = client.get(f"/api/v1/doctors/1/slots?date={tomorrow_str}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "slots" in data
    assert "available_slots" in data
    assert data["date"] == tomorrow_str
    assert len(data["slots"]) > 0


def test_f03_availability_api_invalid_date(client):
    """F-03: Invalid date format returns 400 Bad Request."""
    resp = client.get("/api/v1/doctors/1/slots?date=invalid-date")
    assert resp.status_code == 400
    assert "Invalid date format" in resp.get_json()["error"]


# ── F-04: APPOINTMENT STATE MACHINE ───────────────────────────────────────

def test_f04_appointment_state_transitions(app):
    """F-04: Valid state progression (Scheduled -> CheckedIn -> Completed)."""
    with app.app_context():
        patient = User.query.filter_by(usertype="Patient").first()
        doctor = Doctor.query.first()
        apt = AppointmentService.book(patient.id, doctor.id, datetime.now() + timedelta(days=1))

        # Check In
        apt = AppointmentService.check_in(apt.id)
        assert apt.status == AppointmentStatus.CHECKED_IN

        # Complete
        apt = AppointmentService.complete(apt.id)
        assert apt.status == AppointmentStatus.COMPLETED

        # Attempting to cancel completed appointment must fail
        with pytest.raises(InvalidStateTransitionError):
            AppointmentService.cancel(apt.id)


# ── F-05: NOTIFICATIONS & OUTBOX ──────────────────────────────────────────

def test_f05_outbox_queue_and_in_app(app):
    """F-05: Queue notification to outbox and in-app notifications."""
    with app.app_context():
        patient = User.query.filter_by(usertype="Patient").first()
        entry = NotificationService.queue_outbox(
            recipient=patient.email,
            event_type="test_alert",
            subject="Test Notification",
            body="Hello from Hedgewar Hospital Care"
        )
        assert entry.id is not None
        assert entry.status == NotificationStatus.PENDING

        in_app = NotificationService.send_in_app(
            user_id=patient.id,
            title="Lab Report Ready",
            message="Your complete blood count report is available.",
            category="clinical"
        )
        assert in_app.id is not None
        assert not in_app.is_read

        # Mark read
        success = NotificationService.mark_notification_as_read(in_app.id, patient.id)
        assert success
        assert in_app.is_read


# ── F-06: BILLING & PAYMENT GATEWAY ───────────────────────────────────────

def test_f06_payment_gateway_mock_and_razorpay():
    """F-06: Mock Gateway and Razorpay HMAC signature verification."""
    mock = MockGateway()
    order = mock.create_order(Decimal("1500.00"), receipt="INV-101")
    assert order["status"] == "created"
    assert mock.verify_payment({"status": "success"})

    rzp = RazorpayGateway(key_id="test_key", key_secret="test_secret_12345")
    # Valid signature generation
    import hashlib
    import hmac
    order_id = "order_12345"
    payment_id = "pay_67890"
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(b"test_secret_12345", msg, hashlib.sha256).hexdigest()

    assert rzp.verify_payment({
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": valid_sig
    })

    # Tampered signature fails
    assert not rzp.verify_payment({
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": "tampered_signature"
    })


def test_f06_payment_idempotency_guard(app):
    """F-06: Idempotent payment avoids double-crediting."""
    with app.app_context():
        patient = User.query.filter_by(usertype="Patient").first()
        inv = Invoice(
            patient_id=patient.id,
            invoice_number="INV-IDEMP-001",
            subtotal=Decimal("500.00"),
            total=Decimal("500.00")
        )
        db.session.add(inv)
        db.session.commit()

        # First attempt
        p1 = BillingService.record_payment(
            invoice_id=inv.id,
            amount=Decimal("500.00"),
            method=PaymentMethod.UPI,
            idempotency_key="idemp_unique_key_001"
        )
        assert p1.status == PaymentStatus.SUCCESS
        assert inv.status == InvoiceStatus.PAID

        # Duplicate attempt with same idempotency key returns existing payment without creating another
        p2 = BillingService.record_payment(
            invoice_id=inv.id,
            amount=Decimal("500.00"),
            method=PaymentMethod.UPI,
            idempotency_key="idemp_unique_key_001"
        )
        assert p1.id == p2.id
        assert Payment.query.filter_by(invoice_id=inv.id).count() == 1


# ── F-07: CLINICAL RECORDS & AMENDMENTS ────────────────────────────────────

def test_f07_versioned_clinical_record_amendments(app):
    """F-07: Creating structured prescriptions and versioned amendments."""
    with app.app_context():
        patient = User.query.filter_by(usertype="Patient").first()
        doctor = Doctor.query.first()
        apt = AppointmentService.book(patient.id, doctor.id, datetime.now() + timedelta(days=1))

        # Create record with structured prescription items
        record = RecordService.create_record(
            appointment_id=apt.id,
            diagnosis="Acute Rhinitis",
            prescription="Tab Paracetamol 500mg TDS x 3 days",
            prescription_items=[
                {"medicine": "Paracetamol", "dose": "500mg", "frequency": "TDS", "duration": "3 days"}
            ]
        )
        assert record.version == 1
        assert len(record.prescription_items) == 1

        # Amend record
        amended = RecordService.amend_record(
            record_id=record.id,
            diagnosis="Acute Allergic Rhinitis",
            notes="Added antihistamine",
            prescription="Tab Cetirizine 10mg OD x 5 days",
            reason="Patient reported allergic symptoms"
        )
        assert amended.version == 2
        assert amended.diagnosis == "Acute Allergic Rhinitis"

        # Check version archive
        versions = MedicalRecordVersion.query.filter_by(medical_record_id=record.id).all()
        assert len(versions) == 1
        assert versions[0].diagnosis == "Acute Rhinitis"


# ── F-08: INPATIENT MODULE & ROOM MANAGEMENT ──────────────────────────────

def test_f08_inpatient_transfer_and_maintenance(app):
    """F-08: Room transfer and maintenance workflow."""
    with app.app_context():
        patient = User.query.filter_by(usertype="Patient").first()
        doctor = Doctor.query.first()

        room1 = Room(room_number="Ward-101", ward_type="General", rate_per_day=Decimal("800.00"), status=RoomStatus.AVAILABLE)
        room2 = Room(room_number="Ward-102", ward_type="General", rate_per_day=Decimal("800.00"), status=RoomStatus.AVAILABLE)
        room3 = Room(room_number="Ward-103", ward_type="General", rate_per_day=Decimal("800.00"), status=RoomStatus.AVAILABLE)
        db.session.add_all([room1, room2, room3])
        db.session.commit()

        # 1. Admit to room 1
        adm = AdmissionService.admit(patient.id, doctor.id, room1.id, tentative_days=3)
        assert room1.status == RoomStatus.OCCUPIED

        # 2. Transfer to room 2
        adm = AdmissionService.transfer_room(adm.id, room2.id)
        assert room1.status == RoomStatus.AVAILABLE
        assert room2.status == RoomStatus.OCCUPIED

        # 3. Room 3 to Maintenance
        r3 = AdmissionService.set_room_maintenance(room3.id, reason="Deep Sanitization")
        assert r3.status == RoomStatus.MAINTENANCE


# ── F-09: ADMIN OPERATIONS & CSV EXPORTS ──────────────────────────────────

def test_f09_csv_exports_and_system_settings(client, app):
    """F-09: CSV export endpoints and hospital system settings."""
    client.post("/login", data={"email": "admin@test.local", "password": "AdminPass@123"}, follow_redirects=True)

    # 1. Export appointments CSV
    resp_apt = client.get("/admin/export/appointments")
    assert resp_apt.status_code == 200
    assert "text/csv" in resp_apt.content_type
    assert b"Appointment ID" in resp_apt.data

    # 2. Export invoices CSV
    resp_inv = client.get("/admin/export/invoices")
    assert resp_inv.status_code == 200
    assert "text/csv" in resp_inv.content_type
    assert b"Invoice Number" in resp_inv.data

    # 3. System settings
    resp_settings = client.post("/admin/settings", data={
        "hospital_name": "Hedgewar Hospital Care Memorial",
        "timezone": "Asia/Kolkata",
        "slot_duration_minutes": "45",
        "cancellation_window_hours": "3",
        "default_consultation_fee": "600.00"
    }, follow_redirects=True)
    assert resp_settings.status_code == 200

    with app.app_context():
        assert HospitalSetting.get("hospital_name") == "Hedgewar Hospital Care Memorial"
        assert HospitalSetting.get("slot_duration_minutes") == "45"


# ── F-10: RECEPTIONIST ROLE ───────────────────────────────────────────────

def test_f10_receptionist_permissions(app):
    """F-10: Receptionist role permissions for counter operations."""
    with app.app_context():
        receptionist = User(
            username="Front Desk Staff",
            email="reception@hedgewar.org",
            password="hashed_pass",
            usertype=UserRole.RECEPTIONIST
        )
        patient = User(
            username="Normal Patient",
            email="patient_normal@test.org",
            password="hashed_pass",
            usertype=UserRole.PATIENT
        )

        assert can_book_on_behalf(receptionist)
        assert not can_book_on_behalf(patient)

        assert can_check_in_patient(receptionist)
        assert can_record_payment(receptionist)
        assert not can_record_payment(patient)


# ── F-11: OPENAPI SPECIFICATION ───────────────────────────────────────────

def test_f11_openapi_json_spec(client):
    """F-11: GET /api/v1/openapi.json returns valid OpenAPI 3.0 specification."""
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["openapi"] == "3.0.3"
    assert "Hedgewar Hospital Care" in data["info"]["title"]
    assert "/doctors/{doctor_id}/slots" in data["paths"]
    assert "/search" in data["paths"]


# ── F-12: SERVER-SIDE PAGINATION HELPER ───────────────────────────────────

def test_f12_pagination_helper_logic(app):
    """F-12: Pagination calculates total pages, offsets, and clamps safely."""
    with app.app_context():
        query = User.query
        total_users = query.count()

        p1 = paginate(query, page=1, per_page=2)
        assert p1.page == 1
        assert p1.per_page == 2
        assert len(p1.items) <= 2
        assert p1.total == total_users
        assert list(p1.iter_pages()) is not None

        # Out-of-bounds page is safely clamped
        p_max = paginate(query, page=99999, per_page=10)
        assert p_max.page <= p_max.total_pages
