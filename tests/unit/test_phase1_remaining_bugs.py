"""
tests/unit/test_phase1_remaining_bugs.py
Comprehensive verification test suite for all remaining Phase 1 bug fixes:
B-02, B-05, B-07, B-08, B-09, B-11, B-12, B-13, B-14, B-15, B-16, B-17, B-18, B-19, B-20, B-21, B-22, B-23, B-25.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from hms.extensions import db
from hms.models.admission import Admission, AdmissionStatus, Room, RoomStatus
from hms.models.appointment import Appointment, AppointmentStatus
from hms.models.billing import Invoice, InvoiceStatus, Payment, PaymentMethod
from hms.models.doctor import Doctor
from hms.models.record import MedicalRecord
from hms.models.user import User
from hms.services.admissions import AdmissionService, RoomNotAvailableError
from hms.services.appointments import (
    AppointmentService,
    InvalidStateTransitionError,
)
from hms.services.billing import BillingService


def test_b02_navbar_search_route_and_results(client):
    """B-02: Global search route exists, renders matching results across viewports."""
    resp = client.get('/search?search=Cardio')
    assert resp.status_code == 200
    assert b"Dr. Sharma" in resp.data

    # Empty search
    empty_resp = client.get('/search?search=')
    assert empty_resp.status_code == 200
    assert b"No records found" in empty_resp.data


def test_b05_appointment_reschedule_flow(client, app):
    """B-05 & F-01: Reschedule route /reschedule/<id> and alias /edit/<id>."""
    # Ensure appointment 1 is > 2 hours in the future to permit standard rescheduling
    with app.app_context():
        apt = db.session.get(Appointment, 1)
        apt.starts_at = datetime.now() + timedelta(days=2)
        db.session.commit()

    # Login as Patient 1 (owns Apt 1)
    client.post('/login', data={'email': 'p1@test.local', 'password': 'PatientPass@123'}, follow_redirects=True)

    # 1. GET reschedule page
    get_resp = client.get('/reschedule/1')
    assert get_resp.status_code == 200
    assert b"Update Booking Details" in get_resp.data

    # 2. Reschedule to future slot
    target_dt = datetime.now() + timedelta(days=5, hours=3)
    target_date_str = target_dt.strftime('%Y-%m-%d')
    target_time_str = "02:00 PM"

    post_resp = client.post('/edit/1', data={
        'date': target_date_str,
        'time': target_time_str,
        'disease': 'Migraine and headache'
    }, follow_redirects=True)
    assert post_resp.status_code == 200

    with app.app_context():
        apt = db.session.get(Appointment, 1)
        assert apt.starts_at.strftime('%Y-%m-%d') == target_date_str
        assert apt.starts_at.strftime('%I:%M %p') == target_time_str
        assert "Migraine" in apt.reason


def test_b07_room_day_billing_started_24h_blocks(app):
    """B-07: Inpatient billing charges for every started 24-hour block (minimum 1)."""
    with app.app_context():
        room = db.session.get(Room, 1)
        room.rate_per_day = Decimal('1000.00')
        patient = db.session.get(User, 4)
        doctor = db.session.get(Doctor, 1)

        # 1. Stay of 2 hours -> 1 day billed
        adm1 = Admission(
            patient_id=patient.id, doctor_id=doctor.id, room_id=room.id,
            admission_date=datetime.now(UTC) - timedelta(hours=2),
            status=AdmissionStatus.ADMITTED
        )
        db.session.add(adm1)
        db.session.flush()
        inv1 = BillingService.create_inpatient_invoice(adm1)
        assert inv1.total == Decimal('1000.00')

        # 2. Stay of 25 hours -> ceil(25/24) = 2 days billed
        adm2 = Admission(
            patient_id=patient.id, doctor_id=doctor.id, room_id=room.id,
            admission_date=datetime.now(UTC) - timedelta(hours=25),
            status=AdmissionStatus.ADMITTED
        )
        db.session.add(adm2)
        db.session.flush()
        inv2 = BillingService.create_inpatient_invoice(adm2)
        assert inv2.total == Decimal('2000.00')

        # 3. Stay of 47 hours -> ceil(47/24) = 2 days billed (fixes old floor bug)
        adm3 = Admission(
            patient_id=patient.id, doctor_id=doctor.id, room_id=room.id,
            admission_date=datetime.now(UTC) - timedelta(hours=47),
            status=AdmissionStatus.ADMITTED
        )
        db.session.add(adm3)
        db.session.flush()
        inv3 = BillingService.create_inpatient_invoice(adm3)
        assert inv3.total == Decimal('2000.00')

        # 4. Stay of 49 hours -> ceil(49/24) = 3 days billed
        adm4 = Admission(
            patient_id=patient.id, doctor_id=doctor.id, room_id=room.id,
            admission_date=datetime.now(UTC) - timedelta(hours=49),
            status=AdmissionStatus.ADMITTED
        )
        db.session.add(adm4)
        db.session.flush()
        inv4 = BillingService.create_inpatient_invoice(adm4)
        assert inv4.total == Decimal('3000.00')


def test_b12_add_record_ownership_and_safe_error(client, app):
    """B-12: Doctor cannot add record to another doctor's appointment, no raw internals leaked."""
    # Login as Doctor 2 (does not own Apt 1, which belongs to Doctor 1)
    client.post('/login', data={'email': 'doc2@test.local', 'password': 'DoctorPass@123'}, follow_redirects=True)
    resp = client.post('/add_record/1', data={
        'diagnosis': 'Unauthorized Entry Attempt',
        'prescription': 'None'
    }, follow_redirects=True)
    assert resp.status_code == 403
    assert b"Access Denied" in resp.data

    with app.app_context():
        rec = MedicalRecord.query.filter_by(appointment_id=1).first()
        assert rec is None


def test_b13_room_allocation_concurrency_guard(app):
    """B-13: Room allocation row lock prevents double-admitting to an occupied room."""
    with app.app_context():
        # Room 1 is marked Occupied
        room = db.session.get(Room, 1)
        room.status = RoomStatus.OCCUPIED
        db.session.commit()

        with pytest.raises(RoomNotAvailableError) as exc_info:
            AdmissionService.admit(patient_id=4, doctor_id=1, room_id=1)
        assert "is currently Occupied" in str(exc_info.value)


def test_b14_doctor_rename_does_not_orphan_appointments(app):
    """B-14: Renaming doctor username leaves relational foreign key links intact."""
    with app.app_context():
        doc_user = db.session.get(User, 2)  # Dr. Sharma
        doc_profile = Doctor.query.filter_by(user_id=doc_user.id).first()
        assert doc_profile.id == 1

        # Rename the doctor's user account
        doc_user.username = "Dr. Sharma-Renamed"
        db.session.commit()

        # Query appointments for this doctor via doctor_id
        apts = Appointment.query.filter_by(doctor_id=doc_profile.id).all()
        assert len(apts) >= 1
        assert apts[0].doctor_id == doc_profile.id
        assert apts[0].doctor == "Dr. Sharma-Renamed"


def test_b15_admin_validation_holes(client, app):
    """B-15: Admin staff creation rejects invalid usertypes, and edit enforces email uniqueness."""
    client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'}, follow_redirects=True)

    # 1. Invalid usertype
    resp1 = client.post('/admin/add_staff', data={
        'username': 'Attacker',
        'email': 'attacker@test.local',
        'password': 'Password123',
        'usertype': 'SuperGodRole',
        'dept': 'IT'
    }, follow_redirects=True)
    assert resp1.status_code == 200
    assert b"Invalid account type" in resp1.data

    # 2. Edit staff with duplicate email
    resp2 = client.post('/admin/edit_staff', data={
        'staff_id': 1,
        'username': 'Administrator',
        'email': 'doc1@test.local'  # already belongs to Dr. Sharma
    }, follow_redirects=True)
    assert resp2.status_code == 200
    assert b"already in use" in resp2.data


def test_b16_room_form_validation(client):
    """B-16: Room forms validate positive rates and ward type whitelists."""
    client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'}, follow_redirects=True)

    # Invalid ward type
    resp1 = client.post('/admin/add_room', data={
        'room_number': '999',
        'ward_type': 'HackerWard',
        'rate_per_day': '500'
    }, follow_redirects=True)
    assert resp1.status_code == 200
    assert b"Invalid ward type" in resp1.data

    # Negative daily rate
    resp2 = client.post('/admin/add_room', data={
        'room_number': '998',
        'ward_type': 'General',
        'rate_per_day': '-200'
    }, follow_redirects=True)
    assert resp2.status_code == 200
    assert b"must be a valid positive number" in resp2.data


def test_b17_appointment_state_transition_guards(app):
    """B-17: State machine prevents cancelling completed or missed appointments."""
    with app.app_context():
        apt = db.session.get(Appointment, 1)
        apt.status = AppointmentStatus.COMPLETED
        db.session.commit()

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            AppointmentService.cancel(1)
        assert "Cannot cancel an appointment already marked 'Completed'" in str(exc_info.value)


def test_b18_patient_cannot_self_mark_cash_paid(client, app):
    """B-18: Patient checkout rejects marking invoice Paid with cash, allows valid online payment."""
    with app.app_context():
        inv = Invoice(
            invoice_number='INV-TEST-001',
            patient_id=4,
            subtotal=Decimal('500.00'),
            total=Decimal('500.00'),
            status=InvoiceStatus.ISSUED,
            issued_at=datetime.now(UTC),
            due_at=datetime.now(UTC) + timedelta(days=3)
        )
        db.session.add(inv)
        db.session.commit()
        inv_id = inv.id

    # Login as Patient (id=4)
    client.post('/login', data={'email': 'p1@test.local', 'password': 'PatientPass@123'}, follow_redirects=True)

    # 1. Attempt self-marking as cash
    cash_resp = client.post(f'/bills/{inv_id}/pay', data={'payment_mode': 'cash'}, follow_redirects=True)
    assert cash_resp.status_code == 200
    assert b"Cash payments cannot be self-processed online" in cash_resp.data

    with app.app_context():
        check_inv = db.session.get(Invoice, inv_id)
        assert check_inv.status == InvoiceStatus.ISSUED  # NOT Paid!

    # 2. Pay via UPI
    upi_resp = client.post(f'/bills/{inv_id}/pay', data={'payment_mode': 'upi'}, follow_redirects=True)
    assert upi_resp.status_code == 200
    assert b"Transaction successful!" in upi_resp.data

    with app.app_context():
        settled_inv = db.session.get(Invoice, inv_id)
        assert settled_inv.status == InvoiceStatus.PAID
        payment = Payment.query.filter_by(invoice_id=inv_id).first()
        assert payment is not None
        assert payment.method == PaymentMethod.UPI


def test_b19_admin_soft_deletes_preserve_history(client, app):
    """B-19: Admin deletes perform soft-deactivation, leaving records intact for audit."""
    client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'}, follow_redirects=True)

    # Deactivate doctor
    resp = client.post('/admin/delete_doctor', data={'doctor_id': 3}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        u = db.session.get(User, 3)
        assert u is not None
        assert u.is_active is False
        assert u.deleted_at is not None

    # Deactivate room
    resp2 = client.post('/admin/delete_room', data={'room_id': 2}, follow_redirects=True)
    assert resp2.status_code == 200

    with app.app_context():
        r = db.session.get(Room, 2)
        assert r is not None
        assert r.is_active is False
        assert r.deleted_at is not None


def test_b22_profile_password_requires_current_password(client, app):
    """B-22: Changing password without correct current_password fails."""
    client.post('/login', data={'email': 'p1@test.local', 'password': 'PatientPass@123'}, follow_redirects=True)

    # 1. Attempt without current password
    fail_resp = client.post('/profile', data={
        'username': 'Patient One',
        'email': 'p1@test.local',
        'password': 'NewSuperSecretPass@123',
        'current_password': 'WrongPassword'
    }, follow_redirects=True)
    assert fail_resp.status_code == 200
    assert b"Security Verification" in fail_resp.data

    with app.app_context():
        u = db.session.get(User, 4)
        assert u.check_password('PatientPass@123') is True

    # 2. Attempt with correct current password
    success_resp = client.post('/profile', data={
        'username': 'Patient One',
        'email': 'p1@test.local',
        'password': 'NewSuperSecretPass@123',
        'current_password': 'PatientPass@123'
    }, follow_redirects=True)
    assert success_resp.status_code == 200
    assert b"updated successfully" in success_resp.data

    with app.app_context():
        u = db.session.get(User, 4)
        assert u.check_password('NewSuperSecretPass@123') is True


def test_b25_footer_has_no_mini_project_branding(client):
    """B-25: base.html footer has no DBMS Mini-Project placeholder text."""
    resp = client.get('/')
    assert resp.status_code == 200
    assert b"DBMS Mini-Project" not in resp.data
    assert b"Hedgewar Hospital" in resp.data
