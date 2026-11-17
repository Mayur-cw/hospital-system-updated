from hms.extensions import db
from hms.models.appointment import Appointment
from hms.models.record import MedicalRecord, MedicalRecordVersion, PrescriptionItem
from hms.services.audit import AuditService


class RecordError(Exception):
    pass

class RecordService:
    @staticmethod
    def create_record(appointment_id: int, diagnosis: str,
                      notes: str | None = None, prescription: str | None = None,
                      prescription_items: list[dict[str, str]] | None = None,
                      actor=None) -> MedicalRecord:
        """Create initial medical record for an appointment consultation."""
        apt = db.session.get(Appointment, appointment_id)
        if not apt:
            raise RecordError("Appointment not found.")

        record = MedicalRecord(
            appointment_id=apt.id,
            patient_id=apt.patient_id,
            doctor_id=apt.doctor_id,
            diagnosis=diagnosis.strip(),
            notes=notes.strip() if notes else None,
            prescription=prescription.strip() if prescription else None,
            version=1,
            is_latest=True
        )
        db.session.add(record)
        db.session.flush()

        if prescription_items:
            for item in prescription_items:
                p_item = PrescriptionItem(
                    record_id=record.id,
                    medicine=item.get('medicine', ''),
                    dose=item.get('dose', ''),
                    frequency=item.get('frequency', ''),
                    duration=item.get('duration', ''),
                    instructions=item.get('instructions', '')
                )
                db.session.add(p_item)

        db.session.commit()

        AuditService.record(
            action='RECORD_CREATED',
            entity_type='MedicalRecord',
            entity_id=record.id,
            actor=actor,
            after={'diagnosis': record.diagnosis, 'appointment_id': apt.id}
        )
        return record

    @staticmethod
    def amend_record(record_id: int, diagnosis: str, notes: str | None = None,
                     prescription: str | None = None, reason: str = "Clinical amendment",
                     actor=None) -> MedicalRecord:
        """
        Amend a clinical record with an immutable historical version snapshot (D-10).
        """
        record = db.session.get(MedicalRecord, record_id)
        if not record:
            raise RecordError("Medical record not found.")

        # Archive current state into MedicalRecordVersion
        snapshot = MedicalRecordVersion(
            medical_record_id=record.id,
            version=record.version,
            diagnosis=record.diagnosis,
            notes=record.notes,
            prescription=record.prescription,
            amended_by=getattr(actor, 'id', None),
            amendment_reason=reason
        )
        db.session.add(snapshot)

        # Update record with new version
        record.diagnosis = diagnosis.strip()
        if notes is not None:
            record.notes = notes.strip()
        if prescription is not None:
            record.prescription = prescription.strip()
        record.version += 1

        db.session.commit()

        AuditService.record(
            action='RECORD_AMENDED',
            entity_type='MedicalRecord',
            entity_id=record.id,
            actor=actor,
            after={'version': record.version, 'reason': reason}
        )
        return record
