"""
hms/policies.py — Central Object-Level Authorization Policies
Follows the principle of least privilege: Deny by default.
"""

from hms.models.admission import Admission
from hms.models.appointment import Appointment
from hms.models.billing import Invoice
from hms.models.record import MedicalRecord
from hms.models.user import User, UserRole


def can_view_appointment(user: User, appointment: Appointment) -> bool:
    """Determine if a user can view appointment details."""
    if not user or not user.is_authenticated:
        return False
    if user.usertype == UserRole.ADMIN or user.usertype == UserRole.RECEPTIONIST:
        return True
    if user.usertype == UserRole.PATIENT:
        return appointment.patient_id == user.id
    if user.usertype == UserRole.DOCTOR:
        doc = getattr(user, 'doctor_profile', None)
        return doc is not None and appointment.doctor_id == doc.id
    return False


def can_modify_appointment(user: User, appointment: Appointment) -> bool:
    """Determine if a user can reschedule or mutate an appointment."""
    if not user or not user.is_authenticated:
        return False
    if user.usertype == UserRole.ADMIN:
        return True
    if user.usertype == UserRole.PATIENT:
        return appointment.patient_id == user.id
    if user.usertype == UserRole.DOCTOR:
        doc = getattr(user, 'doctor_profile', None)
        return doc is not None and appointment.doctor_id == doc.id
    return False


def can_cancel_appointment(user: User, appointment: Appointment) -> bool:
    """Determine if a user can cancel an appointment."""
    return can_modify_appointment(user, appointment)


def can_view_invoice(user: User, invoice: Invoice) -> bool:
    """Determine if a user can view an invoice or receipt."""
    if not user or not user.is_authenticated:
        return False
    if user.usertype == UserRole.ADMIN or user.usertype == UserRole.RECEPTIONIST:
        return True
    if user.usertype == UserRole.PATIENT:
        return invoice.patient_id == user.id
    return False


def can_record_payment(user: User) -> bool:
    """Only authorized billing staff and administrators can record offline/cash payments."""
    if not user or not user.is_authenticated:
        return False
    return user.usertype in (UserRole.ADMIN, UserRole.RECEPTIONIST)


def can_view_medical_record(user: User, record: MedicalRecord) -> bool:
    """Determine if a user can view a medical record."""
    if not user or not user.is_authenticated:
        return False
    if user.usertype == UserRole.ADMIN:
        return True
    if user.usertype == UserRole.PATIENT:
        return record.patient_id == user.id
    return user.usertype == UserRole.DOCTOR


def can_edit_medical_record(user: User, record: MedicalRecord) -> bool:
    """Determine if a user can create or amend a medical record."""
    if not user or not user.is_authenticated:
        return False
    if user.usertype == UserRole.ADMIN:
        return True
    if user.usertype == UserRole.DOCTOR:
        doc = getattr(user, 'doctor_profile', None)
        return doc is not None and record.doctor_id == doc.id
    return False


def can_manage_admissions(user: User) -> bool:
    """Determine if a user can admit or manage room assignments."""
    if not user or not user.is_authenticated:
        return False
    return user.usertype in (UserRole.ADMIN, UserRole.DOCTOR)


def can_approve_discharge(user: User, admission: Admission) -> bool:
    """Only the attending doctor or admin can medically approve discharge."""
    if not user or not user.is_authenticated:
        return False
    if user.usertype == UserRole.ADMIN:
        return True
    if user.usertype == UserRole.DOCTOR:
        doc = getattr(user, 'doctor_profile', None)
        return doc is not None and admission.doctor_id == doc.id
    return False


def can_manage_staff(user: User) -> bool:
    """Only administrators can provision, edit, or deactivate staff accounts."""
    if not user or not user.is_authenticated:
        return False
    return user.usertype == UserRole.ADMIN
