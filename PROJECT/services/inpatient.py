from datetime import datetime
from decimal import Decimal
from models import db, Admission, Billing, Room, AuditLog

class InpatientService:
    @staticmethod
    def discharge_patient(admission_id, actor=None, discharge_summary=None):
        """
        Unified, idempotent inpatient discharge domain service.
        Called identically by Doctor and Admin discharge routes to enforce
        consistent billing and bed status postconditions.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return False, "Admission record not found.", None

        # Idempotency check: prevent duplicate discharges and double billing
        if admission.status == 'Discharged':
            existing_bill = Billing.query.filter_by(apt_id=admission.apt_id).first()
            return False, f"Patient {admission.patient.username} is already discharged.", existing_bill

        now = datetime.now()
        admission.status = 'Discharged'
        admission.discharge_date = now
        admission.discharge_requested = False
        if discharge_summary:
            admission.discharge_summary = discharge_summary

        # Tariff math using Decimal to avoid floating-point errors
        delta = now - admission.admission_date
        days = delta.days
        if days <= 0:
            days = 1 # Minimum 1 day tariff for same-day stay

        rate_per_day = Decimal(str(admission.room.rate_per_day))
        room_charge = Decimal(days) * rate_per_day
        consultation_fee = Decimal('500.00')
        total_bill_amount = consultation_fee + room_charge

        # Check if an invoice already exists for this appointment
        bill = Billing.query.filter_by(apt_id=admission.apt_id).first()
        if bill:
            bill.amount = total_bill_amount
        else:
            bill = Billing(
                apt_id=admission.apt_id,
                user_id=admission.patient_id,
                amount=total_bill_amount,
                status='Unpaid'
            )
            db.session.add(bill)

        # Free the room
        if admission.room:
            admission.room.status = 'Available'

        # Record audit event
        actor_name = actor.username if actor else 'System'
        audit = AuditLog(
            apt_id=admission.apt_id,
            user_id=admission.patient_id,
            action=f"PATIENT DISCHARGED by {actor_name} (Days: {days}, Bill: Rs.{total_bill_amount})",
            timestamp=now.strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(audit)

        db.session.commit()
        return True, f"Patient {admission.patient.username} discharged successfully! Final bill of Rs.{total_bill_amount} generated.", bill

    @staticmethod
    def request_discharge(admission_id, patient_user, notes=None):
        """
        Patient-initiated request for discharge review. Sets admission flag
        and records patient notes for the attending physician.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return False, "Admission record not found."
        
        if admission.patient_id != patient_user.id:
            return False, "Access Denied: You cannot request discharge for another patient."
            
        if admission.status == 'Discharged':
            return False, "You are already discharged from this inpatient stay."
            
        admission.discharge_requested = True
        admission.discharge_requested_at = datetime.now()
        if notes:
            admission.discharge_notes = notes.strip()
            
        # Log patient discharge request
        audit = AuditLog(
            apt_id=admission.apt_id,
            user_id=patient_user.id,
            action=f"DISCHARGE REQUESTED by Patient {patient_user.username} (Room: {admission.room.room_number})",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(audit)
        db.session.commit()
        return True, "Your discharge request has been submitted to your attending medical team. Clearance rounds will be conducted shortly."

    @staticmethod
    def get_or_create_interim_bill(admission_id):
        """
        Retrieves or generates an interim invoice for an active inpatient admission
        so the patient can review and settle fees at any point.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return None
            
        bill = Billing.query.filter_by(apt_id=admission.apt_id).first()
        if not bill:
            now = datetime.now()
            delta = now - admission.admission_date
            days = max(1, delta.days)
            rate_per_day = Decimal(str(admission.room.rate_per_day))
            total_amount = Decimal('500.00') + (Decimal(days) * rate_per_day)
            
            bill = Billing(
                apt_id=admission.apt_id,
                user_id=admission.patient_id,
                amount=total_amount,
                status='Unpaid'
            )
            db.session.add(bill)
            db.session.commit()
        return bill
