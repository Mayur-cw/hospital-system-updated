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
        # Lock room row for update to eliminate admission race condition (B-13)
        room = Room.query.filter_by(id=room_id).with_for_update().first()
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

    @staticmethod
    def transfer_room(admission_id: int, new_room_id: int, actor=None) -> Admission:
        """Transfer admitted patient to another available room (F-08)."""
        admission = Admission.query.filter_by(id=admission_id).with_for_update().first()
        if not admission:
            raise AdmissionError("Admission record not found.")

        if admission.status != AdmissionStatus.ADMITTED:
            raise AdmissionError(f"Cannot transfer patient in '{admission.status}' state.")

        if admission.room_id == new_room_id:
            return admission

        new_room = Room.query.filter_by(id=new_room_id).with_for_update().first()
        if not new_room:
            raise AdmissionError("Target room not found.")
        if new_room.status != RoomStatus.AVAILABLE:
            raise RoomNotAvailableError(f"Target room {new_room.room_number} is {new_room.status}.")

        old_room = admission.room
        if old_room:
            old_room.status = RoomStatus.AVAILABLE

        new_room.status = RoomStatus.OCCUPIED
        admission.room_id = new_room.id
        db.session.commit()

        AuditService.record(
            action='PATIENT_TRANSFERRED',
            entity_type='Admission',
            entity_id=admission.id,
            actor=actor,
            before={'room_id': old_room.id if old_room else None},
            after={'room_id': new_room.id}
        )
        return admission

    @staticmethod
    def set_room_maintenance(room_id: int, reason: str = "Sanitization and Maintenance", actor=None) -> Room:
        """Place an available room into maintenance mode (F-08)."""
        room = Room.query.filter_by(id=room_id).with_for_update().first()
        if not room:
            raise AdmissionError("Room not found.")
        if room.status == RoomStatus.OCCUPIED:
            raise AdmissionError("Cannot place an occupied room into maintenance.")

        room.status = RoomStatus.MAINTENANCE
        db.session.commit()

        AuditService.record(
            action='ROOM_MAINTENANCE',
            entity_type='Room',
            entity_id=room.id,
            actor=actor,
            after={'status': room.status, 'reason': reason}
        )
        return room
