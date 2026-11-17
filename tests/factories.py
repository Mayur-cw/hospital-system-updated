# tests/factories.py - Model factories using factory_boy (T-02)
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import factory
from werkzeug.security import generate_password_hash

from hms.extensions import db
from hms.models import (
    Admission,
    AdmissionStatus,
    Appointment,
    AppointmentStatus,
    Department,
    Doctor,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    MedicalRecord,
    PatientProfile,
    Payment,
    PaymentMethod,
    PaymentStatus,
    PrescriptionItem,
    Room,
    RoomStatus,
    User,
    UserRole,
)


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"


class UserFactory(BaseFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@hedgewar.local")
    password = factory.LazyFunction(lambda: generate_password_hash("StrongPass@123"))
    usertype = UserRole.PATIENT.value
    phone = factory.Sequence(lambda n: f"555-0{n:03d}")
    gender = "Other"
    is_active = True


class DepartmentFactory(BaseFactory):
    class Meta:
        model = Department

    name = factory.Sequence(lambda n: f"Department_{n}")
    code = factory.Sequence(lambda n: f"DEP{n:02d}")
    description = "Specialized medical department"
    is_active = True


class DoctorFactory(BaseFactory):
    class Meta:
        model = Doctor

    user = factory.SubFactory(UserFactory, usertype=UserRole.DOCTOR.value)
    department = factory.SubFactory(DepartmentFactory)
    consultation_fee = Decimal("500.00")
    qualifications = "MBBS, MD"
    is_active = True


class PatientProfileFactory(BaseFactory):
    class Meta:
        model = PatientProfile

    user = factory.SubFactory(UserFactory, usertype=UserRole.PATIENT.value)
    blood_group = "O+"
    allergies = "None"
    chronic_conditions = "None"


class RoomFactory(BaseFactory):
    class Meta:
        model = Room

    room_number = factory.Sequence(lambda n: f"R-{n:03d}")
    ward_type = "General"
    rate_per_day = Decimal("800.00")
    status = RoomStatus.AVAILABLE.value
    is_active = True


class AppointmentFactory(BaseFactory):
    class Meta:
        model = Appointment

    patient = factory.SubFactory(UserFactory, usertype=UserRole.PATIENT.value)
    doctor_rel = factory.SubFactory(DoctorFactory)
    department = factory.LazyAttribute(lambda o: o.doctor_rel.department)
    starts_at = factory.LazyFunction(lambda: datetime.now(UTC) + timedelta(days=1))
    duration_min = 30
    status = AppointmentStatus.SCHEDULED.value
    reason = "General consultation"
    is_active = True


class AdmissionFactory(BaseFactory):
    class Meta:
        model = Admission

    patient = factory.SubFactory(UserFactory, usertype=UserRole.PATIENT.value)
    doctor = factory.SubFactory(DoctorFactory)
    room = factory.SubFactory(RoomFactory, status=RoomStatus.OCCUPIED.value)
    admitted_at = factory.LazyFunction(lambda: datetime.now(UTC) - timedelta(days=2))
    expected_discharge_at = factory.LazyFunction(lambda: datetime.now(UTC) + timedelta(days=3))
    status = AdmissionStatus.ADMITTED.value


class InvoiceFactory(BaseFactory):
    class Meta:
        model = Invoice

    invoice_number = factory.Sequence(lambda n: f"INV-2026-{n:06d}")
    patient = factory.SubFactory(UserFactory, usertype=UserRole.PATIENT.value)
    status = InvoiceStatus.ISSUED.value
    subtotal = Decimal("1000.00")
    tax = Decimal("0.00")
    discount = Decimal("0.00")
    total = Decimal("1000.00")


class InvoiceItemFactory(BaseFactory):
    class Meta:
        model = InvoiceItem

    invoice = factory.SubFactory(InvoiceFactory)
    description = "Consultation Service"
    quantity = 1
    unit_price = Decimal("1000.00")
    total = Decimal("1000.00")


class PaymentFactory(BaseFactory):
    class Meta:
        model = Payment

    invoice = factory.SubFactory(InvoiceFactory)
    method = PaymentMethod.ONLINE.value
    amount = factory.LazyAttribute(lambda o: o.invoice.total)
    status = PaymentStatus.SUCCEEDED.value
    idempotency_key = factory.Sequence(lambda n: f"idemp-key-{n:06d}")


class MedicalRecordFactory(BaseFactory):
    class Meta:
        model = MedicalRecord

    patient = factory.SubFactory(UserFactory, usertype=UserRole.PATIENT.value)
    doctor = factory.SubFactory(DoctorFactory)
    appointment = factory.SubFactory(AppointmentFactory)
    diagnosis = "Acute viral infection"
    notes = "Mild fever and cough, advised rest"
    prescription = "Paracetamol 500mg TDS for 3 days"


class PrescriptionItemFactory(BaseFactory):
    class Meta:
        model = PrescriptionItem

    record = factory.SubFactory(MedicalRecordFactory)
    medicine = "Paracetamol 500mg"
    dose = "1 tablet"
    frequency = "TDS"
    duration = "3 days"
    instructions = "After meals"
