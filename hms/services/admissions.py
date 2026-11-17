from datetime import UTC, datetime

from hms.extensions import db
from hms.models.admission import Admission, AdmissionStatus, Room, RoomStatus
from hms.policies import can_approve_discharge
from hms.services.audit import AuditService
from hms.services.billing import BillingService


class AdmissionError(Exception):
    pass

class RoomNotAvailableError(AdmissionError):
    pass

class AdmissionService:
    @staticmethod
    def admit(patient_id: int, doctor_id: int, room_id: int,
              appointment_id: int | None = None, tentative_days: int = 1,
              actor=None) -> Admission:
        """Admit a patient to an available hospital room."""
        room = db.session.get(Room, room_id)
        if not room:
            raise AdmissionError("Room not found.")

        if room.status != RoomStatus.AVAILABLE:
            raise RoomNotAvailableError(f"Room {room.room_number} is currently {room.status}.")

        room.status = RoomStatus.OCCUPIED

        admission = Admission(
            patient_id=patient_id,
            doctor_id=doctor_id,
            room_id=room.id,
            appointment_id=appointment_id,
            admission_date=datetime.now(UTC),
            tentative_days=max(1, tentative_days),
            status=AdmissionStatus.ADMITTED
        )
        db.session.add(admission)
        db.session.commit()

        AuditService.record(
            action='PATIENT_ADMITTED',
            entity_type='Admission',
            entity_id=admission.id,
            actor=actor,
            after={
                'patient_id': patient_id,
                'room_number': room.room_number,
                'tentative_days': tentative_days
            }
        )
        return admission

    @staticmethod
    def request_discharge(admission_id: int, actor=None) -> Admission:
        """Patient requests early discharge from hospital."""
        admission = db.session.get(Admission, admission_id)
        if not admission:
            raise AdmissionError("Admission not found.")

        if admission.status != AdmissionStatus.ADMITTED:
            raise AdmissionError(f"Cannot request discharge for admission in '{admission.status}' state.")

        admission.status = AdmissionStatus.DISCHARGE_REQUESTED
        db.session.commit()

        AuditService.record(
            action='DISCHARGE_REQUESTED',
            entity_type='Admission',
            entity_id=admission.id,
            actor=actor
        )
        return admission

    @staticmethod
    def approve_discharge(admission_id: int, actor=None, notes: str | None = None) -> Admission:
        """Attending doctor medically clears and approves discharge."""
        admission = db.session.get(Admission, admission_id)
        if not admission:
            raise AdmissionError("Admission not found.")

        if actor and not can_approve_discharge(actor, admission):
            raise AdmissionError("Unauthorized: Only the attending physician can approve clinical discharge.")

        admission.status = AdmissionStatus.DISCHARGE_APPROVED
        if notes:
            admission.discharge_notes = notes
        db.session.commit()

        AuditService.record(
            action='DISCHARGE_APPROVED',
            entity_type='Admission',
            entity_id=admission.id,
            actor=actor,
            after={'notes': notes}
        )
        return admission

    @staticmethod
    def discharge(admission_id: int, actor=None) -> Admission:
        """
        Consolidated idempotent discharge flow (resolves B-06).
        Row-locks the admission, frees room, marks discharged, and creates itemized final bill.
        """
        # Lock row for update to prevent concurrent double-discharge
        admission = Admission.query.filter_by(id=admission_id).with_for_update().first()
        if not admission:
            raise AdmissionError("Admission record not found.")

        # Idempotency guard
        if admission.status == AdmissionStatus.DISCHARGED:
            return admission

        now = datetime.now(UTC)
        admission.status = AdmissionStatus.DISCHARGED
        admission.discharge_date = now

        # Free the room
        if admission.room:
            admission.room.status = RoomStatus.AVAILABLE

        # Generate final bill
        invoice = BillingService.create_inpatient_invoice(admission, actor=actor)

        db.session.commit()

        AuditService.record(
            action='PATIENT_DISCHARGED',
            entity_type='Admission',
            entity_id=admission.id,
            actor=actor,
            after={
                'discharge_date': now.isoformat(),
                'invoice_id': invoice.id,
                'total_amount': str(invoice.total)
            }
        )
        return admission
