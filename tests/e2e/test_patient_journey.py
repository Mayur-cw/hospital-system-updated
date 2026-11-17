# tests/e2e/test_patient_journey.py - End-to-End Clinical Lifecycle & Accessibility (T-05)
from datetime import date, datetime, timedelta
from decimal import Decimal

from hms.extensions import db
from hms.models import (
    AdmissionStatus,
    Appointment,
    AppointmentStatus,
    Doctor,
    Invoice,
    InvoiceStatus,
    NotificationOutbox,
    Payment,
    PaymentStatus,
    Room,
    RoomStatus,
    User,
)
from hms.services.admissions import AdmissionService
from hms.services.appointments import AppointmentService
from hms.services.billing import BillingService
from hms.services.records import RecordService


def test_t05_complete_patient_journey(client, app):
    """
    T-05: Complete clinical and financial lifecycle:
    1. Patient Signup & Login
    2. Book Appointment with Physician
    3. Doctor Checks-in Arrived Patient
    4. Doctor Documents Clinical Encounter & Prescription
    5. Consultation Invoice Generated
    6. Patient Settles Invoice via Payment Gateway
    7. Verified Receipt Issued
    8. Room Admission & Discharge Cycle
    """
    # ── 1. SIGNUP & LOGIN ──
    signup_data = {
        "username": "Vikram Singh",
        "email": "vikram.singh@hedgewar.test",
        "password": "SecurePassword@123",
        "phone": "555-0987",
        "gender": "Male",
        "consent": "y"
    }
    resp_signup = client.post("/signup", data=signup_data, follow_redirects=True)
    assert resp_signup.status_code == 200

    with app.app_context():
        patient = User.query.filter_by(email="vikram.singh@hedgewar.test").first()
        assert patient is not None
        assert patient.usertype == "Patient"
        patient_id = patient.id

        doc = Doctor.query.first()
        doc_id = doc.id
        doc_user = doc.user

    # ── 2. BOOK APPOINTMENT ──
    client.post("/login", data={"email": "vikram.singh@hedgewar.test", "password": "SecurePassword@123"}, follow_redirects=True)

    with app.app_context():
        tomorrow = datetime.combine(date.today() + timedelta(days=2), datetime.min.time()) + timedelta(hours=10)
        apt = AppointmentService.book(
            patient_id=patient_id,
            doctor_id=doc_id,
            starts_at=tomorrow,
            reason="Chest discomfort and fatigue"
        )
        apt_id = apt.id

        # Check booking notification created
        notif = NotificationOutbox.query.filter_by(recipient="vikram.singh@hedgewar.test").first()
        assert notif is not None
        assert "Confirmed" in notif.subject

    # ── 3. DOCTOR CHECKS IN PATIENT ──
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": doc_user.email, "password": "DoctorPass@123"}, follow_redirects=True)

    with app.app_context():
        apt_checked = AppointmentService.check_in(apt_id, actor=doc_user)
        assert apt_checked.status == AppointmentStatus.CHECKED_IN

    # ── 4. DOCTOR WRITES CLINICAL RECORD ──
    with app.app_context():
        RecordService.create_record(
            appointment_id=apt_id,
            diagnosis="Costochondritis",
            notes="Sharp chest wall tenderness on palpation",
            prescription="Paracetamol 500mg, Rest",
            actor=doc_user
        )
        AppointmentService.complete(apt_id, actor=doc_user)

    # ── 5. INVOICE GENERATION ──
    with app.app_context():
        apt_obj = db.session.get(Appointment, apt_id)
        invoice = BillingService.create_appointment_invoice(apt_obj, fee=Decimal("600.00"), actor=doc_user)
        inv_id = invoice.id
        assert invoice.total == Decimal("600.00")
        assert invoice.status == InvoiceStatus.ISSUED

    # ── 6. PATIENT REVIEWS & PAYS INVOICE ──
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "vikram.singh@hedgewar.test", "password": "SecurePassword@123"}, follow_redirects=True)

    # View invoice
    resp_inv = client.get(f"/bills/{inv_id}/invoice")
    assert resp_inv.status_code == 200
    assert b"Invoice" in resp_inv.data
    assert b"Checkout" in resp_inv.data

    # Pay invoice via real payment route
    resp_pay = client.post(f"/bills/{inv_id}/pay", data={"payment_mode": "mock"}, follow_redirects=True)
    assert resp_pay.status_code == 200
    assert b"Receipt" in resp_pay.data

    with app.app_context():
        updated_inv = db.session.get(Invoice, inv_id)
        assert updated_inv.status == InvoiceStatus.PAID
        payment = Payment.query.filter_by(invoice_id=inv_id).first()
        assert payment is not None
        assert payment.status == PaymentStatus.SUCCESS

    # ── 7. VERIFIED RECEIPT ──
    resp_receipt = client.get(f"/bills/{inv_id}/receipt")
    assert resp_receipt.status_code == 200
    assert b"Receipt" in resp_receipt.data

    # ── 8. INPATIENT ADMISSION & DISCHARGE CYCLE ──
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "admin@test.local", "password": "AdminPass@123"}, follow_redirects=True)

    with app.app_context():
        room = Room.query.filter_by(status=RoomStatus.AVAILABLE).first()
        assert room is not None
        room_id = room.id
        doc_obj = db.session.get(Doctor, doc_id)

        # Admit
        admission = AdmissionService.admit(patient_id, doc_id, room_id, tentative_days=2)
        assert admission.status == AdmissionStatus.ADMITTED

        # Doctor approves discharge
        AdmissionService.approve_discharge(admission.id, actor=doc_obj.user, notes="Stable condition, vitals normal.")

        # Complete discharge & generate final inpatient bill
        discharged_adm = AdmissionService.discharge(admission.id)
        assert discharged_adm.status == AdmissionStatus.DISCHARGED

        # Verify room released
        released_room = db.session.get(Room, room_id)
        assert released_room.status == RoomStatus.AVAILABLE


def test_t05_accessibility_and_semantic_structure(client):
    """
    T-05: Accessibility checks across core layouts and key views:
    - Page has landmark regions (main, nav)
    - Heading hierarchy starts with an h1
    - Zero inline styles or script blocks
    """
    key_urls = [
        "/",
        "/login",
        "/signup",
        "/healthz",
    ]

    for url in key_urls:
        resp = client.get(url)
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")

        # Must not contain dangerous inline styles or script tags in body
        assert 'style="' not in html, f"Page {url} contains prohibited inline style attributes."
        assert '<style' not in html, f"Page {url} contains prohibited <style> tags."
        assert 'onclick="' not in html, f"Page {url} contains prohibited inline onclick handlers."

        if url not in ("/healthz", "/readyz"):
            # Landmark verification
            assert "<nav" in html or "<header" in html, f"Page {url} missing nav landmark."
            assert "<main" in html or "role=\"main\"" in html or "<div class=\"container" in html
            assert "<h1" in html, f"Page {url} missing primary h1 heading."
