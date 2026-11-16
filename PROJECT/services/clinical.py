from datetime import datetime
from decimal import Decimal
from models import db, MedicalRecord, ClinicalNoteRevision, Appointments, Billing, Room, Admission, Doctors, AuditLog

class ClinicalService:
    @staticmethod
    def save_medical_record(apt_id, diagnosis, prescription, notes, doctor_user, action='sign', room_id=None):
        """Create a new signed or draft clinical record."""
        appointment = Appointments.query.get(apt_id)
        if not appointment:
            return False, "Appointment not found.", None

        existing_record = MedicalRecord.query.filter_by(apt_id=apt_id).first()
        if existing_record:
            return False, "A medical record already exists for this appointment.", existing_record

        try:
            status = 'Signed' if action == 'sign' else 'Draft'
            signed_at = datetime.utcnow() if action == 'sign' else None
            signed_by = doctor_user.username if action == 'sign' else None

            record = MedicalRecord(
                apt_id=apt_id,
                diagnosis=diagnosis,
                prescription=prescription,
                notes=notes,
                status=status,
                signed_by=signed_by,
                signed_at=signed_at
            )
            db.session.add(record)

            # Inpatient admission requested
            if room_id:
                room = Room.query.get(room_id)
                if room and room.status == 'Available':
                    doc_profile = Doctors.query.filter_by(user_id=doctor_user.id).first()
                    doc_did = doc_profile.did if doc_profile else 1
                    
                    admission = Admission(
                        apt_id=apt_id,
                        patient_id=appointment.user_id,
                        doctor_id=doc_did,
                        room_id=room.room_id,
                        status='Admitted'
                    )
                    room.status = 'Occupied'
                    db.session.add(admission)

                    # Initial admission deposit invoice (consultation + 1-day room tariff)
                    existing_bill = Billing.query.filter_by(apt_id=apt_id).first()
                    if not existing_bill:
                        deposit_amount = Decimal('500.00') + Decimal(str(room.rate_per_day))
                        bill = Billing(
                            apt_id=apt_id,
                            user_id=appointment.user_id,
                            amount=deposit_amount,
                            status='Unpaid'
                        )
                        db.session.add(bill)

                    appointment.slot = 'Completed'
                    db.session.commit()
                    return True, "Medical record signed and Patient Admitted to Room. Admission deposit invoice generated.", record

            # Standard Outpatient Logic (Create Rs. 500 consultation invoice)
            existing_bill = Billing.query.filter_by(apt_id=apt_id).first()
            if not existing_bill:
                bill = Billing(
                    apt_id=apt_id,
                    user_id=appointment.user_id,
                    amount=Decimal('500.00'),
                    status='Unpaid'
                )
                db.session.add(bill)

            appointment.slot = 'Completed'
            db.session.commit()
            return True, "Clinical note signed and Outpatient Invoice generated successfully!", record

        except Exception as e:
            db.session.rollback()
            return False, f"Failed to save clinical record: {str(e)}", None

    @staticmethod
    def amend_medical_record(record_id, new_diagnosis, new_prescription, amendment_reason, doctor_user):
        """
        Amend an existing signed medical record while immutably preserving the revision history.
        Enforces medical-legal traceability.
        """
        record = MedicalRecord.query.get(record_id)
        if not record:
            return False, "Medical record not found."

        if not amendment_reason or not amendment_reason.strip():
            return False, "An explicit amendment reason is legally required to modify a signed chart note."

        try:
            # Create immutable revision record
            revision = ClinicalNoteRevision(
                record_id=record.record_id,
                amended_by=doctor_user.username,
                previous_diagnosis=record.diagnosis,
                previous_prescription=record.prescription,
                new_diagnosis=new_diagnosis,
                new_prescription=new_prescription,
                amendment_reason=amendment_reason.strip()
            )
            db.session.add(revision)

            # Update the current view
            record.diagnosis = new_diagnosis
            record.prescription = new_prescription
            record.status = 'Amended'

            audit = AuditLog(
                apt_id=record.apt_id,
                user_id=doctor_user.id,
                action=f"CLINICAL NOTE AMENDED by {doctor_user.username} (Reason: {amendment_reason.strip()[:40]})",
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            db.session.add(audit)
            db.session.commit()

            return True, "Medical record successfully amended. Historical revision preserved in audit trail."

        except Exception as e:
            db.session.rollback()
            return False, f"Failed to amend medical record: {str(e)}"
