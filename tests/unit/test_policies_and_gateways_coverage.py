# tests/unit/test_policies_and_gateways_coverage.py - High-Coverage Policy & Gateway Tests (T-01, S-05)
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from hms.extensions import db
from hms.models import (
    Admission,
    AdmissionStatus,
    Appointment,
    AppointmentStatus,
    Doctor,
    Invoice,
    MedicalRecord,
    Room,
    RoomStatus,
    User,
    UserRole,
)
from hms.policies import (
    can_approve_discharge,
    can_book_on_behalf,
    can_cancel_appointment,
    can_check_in_patient,
    can_edit_medical_record,
    can_manage_admissions,
    can_manage_staff,
    can_modify_appointment,
    can_record_payment,
    can_view_appointment,
    can_view_invoice,
    can_view_medical_record,
)
from hms.services.admissions import AdmissionService, RoomNotAvailableError
from hms.services.notifications import NotificationService
from hms.services.payment_gateway import (
    MockGateway,
    RazorpayGateway,
    get_payment_gateway,
)


def test_rbac_policies_comprehensive(app):
    """T-01, S-05: Comprehensive tests of all object-level authorization policies."""
    with app.app_context():
        admin = User.query.filter_by(usertype="Admin").first()
        doc = Doctor.query.first()
        doc_user = doc.user
        patient = User.query.filter_by(usertype="Patient").first()
        other_patient = User.query.filter(User.usertype == "Patient", User.id != patient.id).first()
        receptionist = User(username="Recep", email="recep@test.local", password="pwd", usertype=UserRole.RECEPTIONIST)
        db.session.add(receptionist)
        db.session.commit()

        # Unauthenticated / None
        assert not can_view_appointment(None, None)
        assert not can_cancel_appointment(None, None)
        assert not can_modify_appointment(None, None)
        assert not can_view_medical_record(None, None)
        assert not can_edit_medical_record(None, None)
        assert not can_view_invoice(None, None)
        assert not can_record_payment(None)
        assert not can_manage_admissions(None)
        assert not can_approve_discharge(None, None)
        assert not can_manage_staff(None)
        assert not can_book_on_behalf(None)
        assert not can_check_in_patient(None)

        # Admin powers
        assert can_manage_staff(admin)
        assert can_record_payment(admin)
        assert can_book_on_behalf(admin)
        assert can_check_in_patient(admin)

        # Receptionist powers
        assert not can_manage_staff(receptionist)
        assert can_record_payment(receptionist)
        assert can_book_on_behalf(receptionist)
        assert can_check_in_patient(receptionist)

        # Patient appointment access
        apt = Appointment(
            patient_id=patient.id,
            doctor_id=doc.id,
            starts_at=datetime.now(UTC) + timedelta(days=1),
            status=AppointmentStatus.SCHEDULED
        )
        db.session.add(apt)
        db.session.commit()

        assert can_view_appointment(patient, apt)
        assert not can_view_appointment(other_patient, apt)
        assert can_view_appointment(admin, apt)
        assert can_view_appointment(doc_user, apt)

        assert can_cancel_appointment(patient, apt)
        assert not can_cancel_appointment(other_patient, apt)
        assert can_cancel_appointment(admin, apt)
        assert can_cancel_appointment(doc_user, apt)

        assert can_modify_appointment(patient, apt)
        assert not can_modify_appointment(other_patient, apt)

        # Invoice access
        inv = Invoice(invoice_number="INV-POLICY-01", patient_id=patient.id, subtotal=Decimal("100"), total=Decimal("100"))
        db.session.add(inv)
        db.session.commit()

        assert can_view_invoice(patient, inv)
        assert not can_view_invoice(other_patient, inv)
        assert can_view_invoice(admin, inv)
        assert can_view_invoice(receptionist, inv)
        assert not can_view_invoice(doc_user, inv)

        # Medical record access
        rec = MedicalRecord(appointment_id=apt.id, patient_id=patient.id, doctor_id=doc.id, diagnosis="Hypertension", notes="Rest")
        db.session.add(rec)
        db.session.commit()

        assert can_view_medical_record(admin, rec)
        assert can_view_medical_record(doc_user, rec)
        assert can_view_medical_record(patient, rec)
        assert not can_view_medical_record(other_patient, rec)
        assert not can_view_medical_record(receptionist, rec)

        doc2 = Doctor.query.filter(Doctor.id != doc.id).first()
        if doc2:
            assert can_edit_medical_record(admin, rec)
            assert can_edit_medical_record(doc_user, rec)
            assert not can_edit_medical_record(doc2.user, rec)
            assert not can_edit_medical_record(patient, rec)
            assert can_modify_appointment(doc_user, apt)
            assert not can_modify_appointment(doc2.user, apt)

        # Admission discharge access
        room = Room.query.first()
        adm = Admission(patient_id=patient.id, doctor_id=doc.id, room_id=room.id, status=AdmissionStatus.ADMITTED)
        db.session.add(adm)
        db.session.commit()

        assert can_manage_admissions(admin)
        assert can_manage_admissions(doc_user)
        assert not can_manage_admissions(patient)

        assert can_approve_discharge(admin, adm)
        assert can_approve_discharge(doc_user, adm)
        if doc2:
            assert not can_approve_discharge(doc2.user, adm)
        assert not can_approve_discharge(patient, adm)


def test_payment_gateway_implementations(app, monkeypatch):
    """T-01, F-06: Test PaymentGateway interface, MockGateway, and RazorpayGateway."""
    # 1. Factory lookup
    monkeypatch.setenv("PAYMENT_GATEWAY", "mock")
    mock_gw = get_payment_gateway()
    assert isinstance(mock_gw, MockGateway)
    monkeypatch.setenv("PAYMENT_GATEWAY", "razorpay")
    rz_gw = get_payment_gateway()
    assert isinstance(rz_gw, RazorpayGateway)

    # 2. MockGateway execution
    order = mock_gw.create_order(Decimal("1250.00"), currency="INR", receipt="RCP-001")
    assert order["amount"] == 1250.0
    assert order["status"] == "created"
    assert "order_id" in order

    # Successful verification
    verify_res = mock_gw.verify_payment({"order_id": order["order_id"], "status": "success"})
    assert verify_res is True

    # Failed verification
    verify_fail = mock_gw.verify_payment({"order_id": order["order_id"], "status": "failed"})
    assert verify_fail is False

    # 3. RazorpayGateway signature verification
    rz_gw.key_secret = "test_secret_key"
    import hashlib
    import hmac
    valid_sig = hmac.new(b"test_secret_key", b"order_rzp_123|pay_rzp_456", hashlib.sha256).hexdigest()

    payload_valid = {"razorpay_order_id": "order_rzp_123", "razorpay_payment_id": "pay_rzp_456", "razorpay_signature": valid_sig}
    payload_invalid = {"razorpay_order_id": "order_rzp_123", "razorpay_payment_id": "pay_rzp_456", "razorpay_signature": "tampered_sig"}
    assert rz_gw.verify_payment(payload_valid) is True
    assert rz_gw.verify_payment(payload_invalid) is False


def test_admission_service_transfers_and_maintenance(app):
    """T-01, F-08: Test room transfer and maintenance status transitions."""
    with app.app_context():
        doc = Doctor.query.first()
        patient = User.query.filter_by(usertype="Patient").first()

        r1 = Room(room_number="R-TEST-1", ward_type="General", rate_per_day=Decimal("500"), status=RoomStatus.AVAILABLE)
        r2 = Room(room_number="R-TEST-2", ward_type="Private", rate_per_day=Decimal("1500"), status=RoomStatus.AVAILABLE)
        db.session.add_all([r1, r2])
        db.session.commit()

        # Maintenance transition
        updated_r1 = AdmissionService.set_room_maintenance(r1.id, reason="Sanitization")
        assert updated_r1.status == RoomStatus.MAINTENANCE

        # Return from maintenance
        updated_r1_avail = AdmissionService.set_room_maintenance(r1.id, maintenance=False)
        assert updated_r1_avail.status == RoomStatus.AVAILABLE

        # Admit patient to r1
        adm = AdmissionService.admit(patient.id, doc.id, r1.id, tentative_days=2)
        assert adm.room_id == r1.id
        assert r1.status == RoomStatus.OCCUPIED

        # Transfer from r1 to r2
        transferred_adm = AdmissionService.transfer_room(adm.id, r2.id)
        assert transferred_adm.room_id == r2.id
        assert r1.status == RoomStatus.AVAILABLE
        assert r2.status == RoomStatus.OCCUPIED

        # Make r1 occupied by another admission
        other_patient = User.query.filter(User.usertype == "Patient", User.id != patient.id).first()
        AdmissionService.admit(other_patient.id, doc.id, r1.id, tentative_days=3)
        assert r1.status == RoomStatus.OCCUPIED

        # Attempt invalid transfer to an already occupied room (r1)
        with pytest.raises(RoomNotAvailableError):
            AdmissionService.transfer_room(adm.id, r1.id)


def test_notification_service_edge_cases(app):
    """T-01, F-05: Test unread notification querying and read marking."""
    with app.app_context():
        patient = User.query.filter_by(usertype="Patient").first()

        notif = NotificationService.send_in_app(
            user_id=patient.id,
            title="Lab Results Ready",
            message="Your complete blood count results are available.",
            category="clinical"
        )
        assert notif.id is not None
        assert not notif.is_read

        unreads = NotificationService.get_unread_notifications(patient.id)
        assert any(n.id == notif.id for n in unreads)

        success = NotificationService.mark_notification_as_read(notif.id, patient.id)
        assert success is True

        # Non-existent notification returns False
        assert NotificationService.mark_notification_as_read(999999, patient.id) is False


def test_policy_decorators(app):
    """T-01, S-05: Test roles_required, admin_required, doctor_required, patient_required decorators."""
    from werkzeug.exceptions import Forbidden, Unauthorized

    from hms.policies import admin_required, doctor_required, patient_required, roles_required

    with app.app_context():
        admin = User.query.filter_by(usertype="Admin").first()
        patient = User.query.filter_by(usertype="Patient").first()

    # 1. Unauthenticated web request -> 302 redirect to login
    with app.test_request_context('/admin/dashboard'):
        @admin_required
        def view_admin():
            return "admin_ok"
        res = view_admin()
        assert res.status_code == 302
        assert '/login' in res.headers['Location']

    # 2. Unauthenticated API request -> 401 Unauthorized
    with app.test_request_context('/api/v1/resource'):
        @roles_required(UserRole.ADMIN)
        def view_api():
            return "api_ok"
        with pytest.raises(Unauthorized):
            view_api()

    # 3. Authenticated - Authorized
    with app.test_request_context('/admin/dashboard'):
        from flask_login import login_user
        login_user(admin)
        assert view_admin() == "admin_ok"

    # 4. Authenticated - Forbidden (Patient attempting Admin view)
    with app.test_request_context('/admin/dashboard'):
        from flask_login import login_user
        login_user(patient)
        with pytest.raises(Forbidden):
            view_admin()

    # 5. Doctor required
    with app.test_request_context('/doctor/queue'):
        from flask_login import login_user
        doc_user = User.query.filter_by(usertype="Doctor").first()
        login_user(doc_user)
        @doctor_required
        def view_doc():
            return "doctor_ok"
        assert view_doc() == "doctor_ok"

    # 6. Patient required
    with app.test_request_context('/my_appointments'):
        from flask_login import login_user
        patient_user = User.query.filter_by(usertype="Patient").first()
        login_user(patient_user)
        @patient_required
        def view_pat():
            return "patient_ok"
        assert view_pat() == "patient_ok"


def test_notification_channels_and_templates(app):
    """T-01, F-05: Test all notification dispatch methods in NotificationService."""
    with app.app_context():
        doc = Doctor.query.first()
        patient = User.query.filter_by(usertype="Patient").first()
        apt = Appointment(
            patient_id=patient.id,
            doctor_id=doc.id,
            doctor=doc.user.username,
            starts_at=datetime.now(UTC) + timedelta(days=1),
            status=AppointmentStatus.SCHEDULED,
        )
        inv = Invoice(
            invoice_number="INV-NOTIF-99",
            patient_id=patient.id,
            subtotal=Decimal("200.00"),
            total=Decimal("200.00"),
            status="Issued",
        )
        db.session.add_all([apt, inv])
        db.session.commit()

        from hms.models.billing import Payment
        pay = Payment(
            invoice_id=inv.id,
            amount=Decimal("200.00"),
            method="Cash",
            status="Settled",
            paid_at=datetime.now(UTC),
        )
        db.session.add(pay)
        db.session.commit()

        assert NotificationService.send_appointment_confirmation(apt) is True
        assert NotificationService.send_appointment_reminder(apt) is True
        assert NotificationService.send_reschedule_notification(apt, old_starts_at=datetime.now(UTC)) is True
        assert NotificationService.send_cancellation_notification(apt, reason="Doctor emergency") is True
        assert NotificationService.send_invoice_notification(inv) is True
        assert NotificationService.send_payment_receipt(pay) is True


def test_search_service_scoping(app):
    """T-01, F-02: Test SearchService doctor-scoped patient search."""
    from hms.services.search import SearchService
    with app.app_context():
        doc = Doctor.query.first()
        patient = User.query.filter_by(usertype="Patient").first()

        apt = Appointment(
            patient_id=patient.id,
            doctor_id=doc.id,
            starts_at=datetime.now(UTC) + timedelta(days=2),
            status=AppointmentStatus.SCHEDULED,
        )
        db.session.add(apt)
        db.session.commit()

        # Doctor queries patients they treat
        results = SearchService.global_search(patient.username[:4], current_user=doc.user)
        assert isinstance(results, list)


def test_admission_service_validation_errors(app):
    """T-01, F-08: Test AdmissionService error conditions."""
    from hms.services.admissions import AdmissionError, AdmissionService
    with app.app_context():
        doc = Doctor.query.first()
        patient = User.query.filter_by(usertype="Patient").first()

        # Non-existent room
        with pytest.raises(AdmissionError):
            AdmissionService.admit(patient.id, doc.id, 999999)

        # Invalid admission id for discharge
        with pytest.raises(AdmissionError):
            AdmissionService.request_discharge(999999)

        with pytest.raises(AdmissionError):
            AdmissionService.approve_discharge(999999)

        with pytest.raises(AdmissionError):
            AdmissionService.discharge(999999)

        with pytest.raises(AdmissionError):
            AdmissionService.set_room_maintenance(999999)


def test_notification_service_failure_resilience(app, monkeypatch):
    """T-01, F-05: Test NotificationService error resilience and rollback branches."""
    from unittest.mock import MagicMock
    with app.app_context():
        # Mock commit to raise Exception
        monkeypatch.setattr(db.session, "commit", MagicMock(side_effect=Exception("DB Commit Failure")))
        outbox = NotificationService.queue_outbox("fail@test.local", "test_evt", "sub", "body")
        assert outbox is not None

        notif = NotificationService.send_in_app(1, "title", "msg")
        assert notif is not None

        # When an exception happens inside send helpers (e.g. invalid object missing required relationships)
        inv = Invoice(invoice_number="INV-FAIL", patient_id=999999)
        from hms.models.billing import Payment
        pay = Payment(invoice_id=999999)

        assert NotificationService.send_appointment_confirmation(None) is False
        assert NotificationService.send_appointment_reminder(None) is False
        assert NotificationService.send_reschedule_notification(None, old_starts_at=None) is False
        assert NotificationService.send_cancellation_notification(None) is False
        assert NotificationService.send_invoice_notification(inv) is False
        assert NotificationService.send_payment_receipt(pay) is False
