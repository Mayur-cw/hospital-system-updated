from hms.extensions import db
from hms.models.admission import Admission, AdmissionStatus, Room, RoomStatus
from hms.models.appointment import ActiveSlotExpr, Appointment, AppointmentStatus
from hms.models.audit import AuditEvent
from hms.models.availability import DoctorBreak, DoctorLeave, DoctorSchedule
from hms.models.base import SoftDeleteMixin, TimestampMixin
from hms.models.billing import (
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from hms.models.department import Department
from hms.models.doctor import Doctor
from hms.models.patient import PatientProfile
from hms.models.record import MedicalRecord, MedicalRecordVersion, PrescriptionItem
from hms.models.user import User, UserRole

# Legacy compatibility aliases
Doctors = Doctor
Appointments = Appointment
Billing = Invoice
AuditLog = AuditEvent

__all__ = [
    'ActiveSlotExpr',
    'Admission',
    'AdmissionStatus',
    'Appointment',
    'AppointmentStatus',
    'Appointments',
    'AuditEvent',
    'AuditLog',
    'Billing',
    'Department',
    'Doctor',
    'DoctorBreak',
    'DoctorLeave',
    'DoctorSchedule',
    'Doctors',
    'Invoice',
    'InvoiceItem',
    'InvoiceStatus',
    'MedicalRecord',
    'MedicalRecordVersion',
    'PatientProfile',
    'Payment',
    'PaymentMethod',
    'PaymentStatus',
    'PrescriptionItem',
    'Room',
    'RoomStatus',
    'SoftDeleteMixin',
    'TimestampMixin',
    'User',
    'UserRole',
    'db',
]
