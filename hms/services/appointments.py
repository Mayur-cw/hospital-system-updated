from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from hms.extensions import db
from hms.models.appointment import Appointment, AppointmentStatus
from hms.models.doctor import Doctor
from hms.policies import can_cancel_appointment, can_modify_appointment
from hms.services.audit import AuditService
from hms.services.notifications import NotificationService


class AppointmentError(Exception):
    pass

class SlotAlreadyBookedError(AppointmentError):
    pass

class AppointmentCutoffError(AppointmentError):
    pass

class UnauthorizedAppointmentActionError(AppointmentError):
    pass

class InvalidStateTransitionError(AppointmentError):
    pass

class AppointmentService:
    @staticmethod
    def book(patient_id: int, doctor_id: int, starts_at: datetime,
             duration_min: int = 30, department_id: int | None = None,
             reason: str | None = None, actor=None) -> Appointment:
        """
        Book a new appointment.
        Enforces double-booking safety via database unique constraint on active_slot_key (D-03).
        """
        doc = db.session.get(Doctor, doctor_id)
        if not doc:
            raise AppointmentError(f"Doctor with id {doctor_id} not found.")

        if not department_id and doc.department_id:
            department_id = doc.department_id

        # Round starts_at to minute precision
        starts_at = starts_at.replace(second=0, microsecond=0)

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            department_id=department_id,
            starts_at=starts_at,
            duration_min=duration_min,
            status=AppointmentStatus.SCHEDULED,
            reason=reason
        )

        db.session.add(appointment)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise SlotAlreadyBookedError(
                "The selected appointment slot has already been booked. Please choose another time."
            ) from e

        AuditService.record(
            action='APPOINTMENT_BOOKED',
            entity_type='Appointment',
            entity_id=appointment.id,
            actor=actor or appointment.patient,
            after={
                'doctor_id': doctor_id,
                'patient_id': patient_id,
                'starts_at': starts_at.isoformat(),
                'status': appointment.status
            }
        )
        NotificationService.send_appointment_confirmation(appointment)
        return appointment

    @staticmethod
    def reschedule(appointment_id: int, new_starts_at: datetime,
                   actor=None, reason: str | None = None,
                   cutoff_hours: int = 2) -> Appointment:
        """
        Reschedule an existing appointment (F-01).
        Enforces cutoff window (default >= 2 hours prior to scheduled start).
        """
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise AppointmentError("Appointment not found.")

        if actor and not can_modify_appointment(actor, appointment):
            raise UnauthorizedAppointmentActionError("Unauthorized to reschedule this appointment.")

        if appointment.status != AppointmentStatus.SCHEDULED:
            raise InvalidStateTransitionError(f"Cannot reschedule an appointment in '{appointment.status}' state.")

        # Cutoff verification
        now = datetime.now()
        earliest_allowed = now + timedelta(hours=cutoff_hours)
        if appointment.starts_at < earliest_allowed and not (actor and getattr(actor, 'is_admin', False)):
            raise AppointmentCutoffError(
                f"Appointments cannot be rescheduled less than {cutoff_hours} hours before the start time."
            )

        old_starts_at = appointment.starts_at
        new_starts_at = new_starts_at.replace(second=0, microsecond=0)

        appointment.starts_at = new_starts_at
        appointment.reason = f"Rescheduled: {reason}" if reason else appointment.reason

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise SlotAlreadyBookedError("The target slot is already booked.") from e

        AuditService.record(
            action='APPOINTMENT_RESCHEDULED',
            entity_type='Appointment',
            entity_id=appointment.id,
            actor=actor,
            before={'starts_at': old_starts_at.isoformat()},
            after={'starts_at': new_starts_at.isoformat(), 'reason': reason}
        )
        NotificationService.send_reschedule_notification(appointment, old_starts_at)
        return appointment

    @staticmethod
    def cancel(appointment_id: int, actor=None, reason: str | None = None) -> Appointment:
        """
        Cancel an appointment (F-04).
        Sets status to Cancelled which automatically frees up active_slot_key in MySQL/SQLite.
        """
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise AppointmentError("Appointment not found.")

        if actor and not can_cancel_appointment(actor, appointment):
            raise UnauthorizedAppointmentActionError("Unauthorized to cancel this appointment.")

        if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
            raise InvalidStateTransitionError(f"Cannot cancel an appointment already marked '{appointment.status}'.")

        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_by = getattr(actor, 'id', None)
        appointment.cancel_reason = reason
        db.session.commit()

        AuditService.record(
            action='APPOINTMENT_CANCELLED',
            entity_type='Appointment',
            entity_id=appointment.id,
            actor=actor,
            after={'status': appointment.status, 'cancel_reason': reason}
        )
        NotificationService.send_cancellation_notification(appointment, actor=actor, reason=reason)
        return appointment

    @staticmethod
    def check_in(appointment_id: int, actor=None) -> Appointment:
        """Mark appointment checked in / attended upon patient arrival."""
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise AppointmentError("Appointment not found.")

        if appointment.status != AppointmentStatus.SCHEDULED:
            raise InvalidStateTransitionError(f"Cannot check in appointment in '{appointment.status}' state.")

        appointment.status = AppointmentStatus.CHECKED_IN
        db.session.commit()

        AuditService.record(
            action='APPOINTMENT_CHECKED_IN',
            entity_type='Appointment',
            entity_id=appointment.id,
            actor=actor,
            after={'status': appointment.status}
        )
        return appointment

    @staticmethod
    def complete(appointment_id: int, actor=None) -> Appointment:
        """Mark appointment completed after consultation finishes."""
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise AppointmentError("Appointment not found.")

        appointment.status = AppointmentStatus.COMPLETED
        db.session.commit()

        AuditService.record(
            action='APPOINTMENT_COMPLETED',
            entity_type='Appointment',
            entity_id=appointment.id,
            actor=actor,
            after={'status': appointment.status}
        )
        return appointment

    @staticmethod
    def mark_missed(appointment_id: int, actor=None) -> Appointment:
        """Mark appointment missed if patient failed to show up (R-04)."""
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise AppointmentError("Appointment not found.")

        if appointment.status != AppointmentStatus.SCHEDULED:
            return appointment

        appointment.status = AppointmentStatus.MISSED
        db.session.commit()

        AuditService.record(
            action='APPOINTMENT_MISSED',
            entity_type='Appointment',
            entity_id=appointment.id,
            actor=actor,
            after={'status': appointment.status}
        )
        return appointment
