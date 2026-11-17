from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from hms.extensions import db
from hms.filters import format_currency, format_date, format_time
from hms.models import (
    AdmissionStatus,
    Appointment,
    AppointmentStatus,
    Department,
    Doctor,
    Invoice,
    InvoiceStatus,
    MedicalRecordVersion,
    Payment,
    Room,
    RoomStatus,
    User,
    UserRole,
)
from hms.services import (
    AdmissionService,
    AppointmentCutoffError,
    AppointmentService,
    AvailabilityService,
    BillingService,
    RecordService,
    SlotAlreadyBookedError,
)


def test_phase3_departments_and_doctors(app):
    """D-06: Departments and Doctor relational profiles."""
    with app.app_context():
        cardio = Department.query.filter(
            (Department.name == 'Cardiology') | (Department.code == 'CARD')
        ).first()
        if not cardio:
            cardio = Department(name='Cardiology', code='CARD', description='Heart care')
            db.session.add(cardio)
            db.session.commit()

        u = User(username='Dr. Test', email='doc.test@hospital.local', password='pwd', usertype=UserRole.DOCTOR)
        db.session.add(u)
        db.session.flush()

        doc = Doctor(user_id=u.id, department_id=cardio.id, consultation_fee=Decimal('750.00'), qualifications='MD')
        db.session.add(doc)
        db.session.commit()

        assert doc.id is not None
        assert doc.dept == cardio.name
        assert doc.consultation_fee == Decimal('750.00')
        assert doc.user.username == 'Dr. Test'

def test_phase3_appointment_double_booking_enforcement(app):
    """D-03: Double-booking prevention enforced via active_slot_key and service."""
    with app.app_context():
        target_slot = datetime(2026, 11, 25, 10, 0)

        # 1. Book first appointment
        apt1 = AppointmentService.book(
            patient_id=4,
            doctor_id=1,
            starts_at=target_slot,
            reason="Routine checkup"
        )
        assert apt1.id is not None
        assert apt1.status == AppointmentStatus.SCHEDULED

        # 2. Parallel / duplicate attempt for the same doctor and slot MUST fail
        with pytest.raises(SlotAlreadyBookedError):
            AppointmentService.book(
                patient_id=5,
                doctor_id=1,
                starts_at=target_slot,
                reason="Should be rejected"
            )

        # 3. Cancel first appointment -> frees slot automatically in DB
        AppointmentService.cancel(apt1.id, reason="Patient requested cancellation")
        assert apt1.status == AppointmentStatus.CANCELLED

        # 4. Now booking for that slot succeeds!
        apt2 = AppointmentService.book(
            patient_id=5,
            doctor_id=1,
            starts_at=target_slot,
            reason="Now allowed after cancellation"
        )
        assert apt2.id is not None
        assert apt2.status == AppointmentStatus.SCHEDULED

def test_phase3_appointment_reschedule_cutoff(app):
    """F-01: Reschedule respects cutoff window and availability."""
    with app.app_context():
        now = datetime.now()
        # Appointment within 1 hour (< 2 hour default cutoff)
        soon_slot = now + timedelta(minutes=45)
        apt = Appointment(
            patient_id=4, doctor_id=1, starts_at=soon_slot, status=AppointmentStatus.SCHEDULED
        )
        db.session.add(apt)
        db.session.commit()

        patient_user = db.session.get(User, 4)
        new_slot = now + timedelta(days=2)

        # Patient cannot reschedule within cutoff window
        with pytest.raises(AppointmentCutoffError):
            AppointmentService.reschedule(apt.id, new_starts_at=new_slot, actor=patient_user, cutoff_hours=2)

        # Admin can override cutoff
        admin_user = db.session.get(User, 1)
        rescheduled = AppointmentService.reschedule(apt.id, new_starts_at=new_slot, actor=admin_user, cutoff_hours=2)
        assert rescheduled.starts_at.day == new_slot.day

def test_phase3_money_and_invoices_decimal(app):
    """D-04: Money is Decimal end-to-end; invoices and payments with idempotency."""
    with app.app_context():
        apt = Appointment.query.first()
        invoice = BillingService.create_appointment_invoice(apt, fee=Decimal('650.00'))

        assert isinstance(invoice.total, Decimal)
        assert invoice.total == Decimal('650.00')
        assert invoice.status == InvoiceStatus.ISSUED
        assert invoice.invoice_number.startswith('INV-')

        # Record payment with idempotency key
        idem_key = "test-idem-key-12345"
        payment = BillingService.record_payment(
            invoice_id=invoice.id,
            amount=Decimal('650.00'),
            method='Card',
            idempotency_key=idem_key
        )
        assert payment.id is not None
        assert payment.amount == Decimal('650.00')
        assert invoice.status == InvoiceStatus.PAID

        # Duplicate payment request with same idempotency key returns existing payment without double charging
        dup_payment = BillingService.record_payment(
            invoice_id=invoice.id,
            amount=Decimal('650.00'),
            method='Card',
            idempotency_key=idem_key
        )
        assert dup_payment.id == payment.id
        assert Payment.query.filter_by(idempotency_key=idem_key).count() == 1

def test_phase3_inpatient_admission_and_idempotent_discharge(app):
    """B-06, F-08: Inpatient admission, room occupancy, and idempotent consolidated discharge."""
    with app.app_context():
        # 1. Admit patient to room 101
        room = db.session.get(Room, 1)
        room.status = RoomStatus.AVAILABLE
        db.session.commit()

        admission = AdmissionService.admit(
            patient_id=4,
            doctor_id=1,
            room_id=1,
            tentative_days=3
        )
        assert admission.id is not None
        assert admission.status == AdmissionStatus.ADMITTED
        assert room.status == RoomStatus.OCCUPIED

        # 2. Discharge patient
        AdmissionService.discharge(admission.id)
        assert admission.status == AdmissionStatus.DISCHARGED
        assert room.status == RoomStatus.AVAILABLE

        # Verify final invoice was generated
        invoice = Invoice.query.filter_by(admission_id=admission.id).first()
        assert invoice is not None
        assert invoice.total >= Decimal('800.00')

        # 3. Idempotent check: calling discharge again does NOT create duplicate bills
        inv_count_before = Invoice.query.filter_by(admission_id=admission.id).count()
        AdmissionService.discharge(admission.id)
        inv_count_after = Invoice.query.filter_by(admission_id=admission.id).count()
        assert inv_count_before == inv_count_after == 1

def test_phase3_versioned_medical_records(app):
    """D-10: Clinical records maintain versioned amendment history."""
    with app.app_context():
        apt = Appointment.query.first()

        # 1. Initial record
        record = RecordService.create_record(
            appointment_id=apt.id,
            diagnosis="Type 2 Diabetes Mellitus",
            notes="Initial presentation, FBS 160 mg/dL",
            prescription="Metformin 500mg BD"
        )
        assert record.version == 1
        assert record.diagnosis == "Type 2 Diabetes Mellitus"

        # 2. Amend record -> creates snapshot of v1 in MedicalRecordVersion
        doc_user = db.session.get(User, 2)
        RecordService.amend_record(
            record_id=record.id,
            diagnosis="Type 2 Diabetes Mellitus + Microalbuminuria",
            notes="Added Telmisartan for renal protection",
            prescription="Metformin 500mg BD + Telmisartan 20mg OD",
            reason="Lab reports received showing elevated urine albumin",
            actor=doc_user
        )

        assert record.version == 2
        assert "Microalbuminuria" in record.diagnosis

        # Verify historical version
        history = MedicalRecordVersion.query.filter_by(medical_record_id=record.id).all()
        assert len(history) == 1
        assert history[0].version == 1
        assert history[0].diagnosis == "Type 2 Diabetes Mellitus"
        assert history[0].amendment_reason == "Lab reports received showing elevated urine albumin"

def test_phase3_jinja_en_in_currency_and_time_filters():
    """A-04: en-IN currency and regional time formatting filters."""
    assert format_currency(Decimal('1500.00')) == '₹ 1,500.00'
    assert format_currency(Decimal('150000.50')) == '₹ 1,50,000.50'
    assert format_currency(Decimal(500)) == '₹ 500.00'

    sample_dt = datetime(2026, 11, 17, 10, 30, tzinfo=UTC)
    assert '17 Nov 2026' in format_date(sample_dt)
    assert format_time('14:30') in ('02:30 PM', '14:30')

def test_phase3_availability_service(app):
    """D-08: Server-side slot generation minus booked appointments."""
    with app.app_context():
        test_date = date(2026, 12, 1)
        slots = AvailabilityService.get_available_slots(doctor_id=1, query_date=test_date)
        assert len(slots) > 0
        assert any(s['time'] == '09:00' for s in slots)
        assert any(s['time'] == '10:00' for s in slots)
        # Lunch hour (13:00 - 14:00) should be excluded
        assert not any(s['time'] == '13:00' for s in slots)
        assert not any(s['time'] == '13:30' for s in slots)
