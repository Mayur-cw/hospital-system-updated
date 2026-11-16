from datetime import datetime
from decimal import Decimal
from models import db, Admission, Billing, Room, AuditLog

class InpatientService:
    @staticmethod
    def _can_doctor_manage(user, admission):
        if not user:
            return False
        usertype = getattr(user, 'usertype', None)
        if usertype == 'Admin':
            return True
        if usertype == 'Doctor':
            if admission.doctor and getattr(admission.doctor, 'user_id', None) == user.id:
                return True
            if admission.doctor_id == user.id:
                return True
        return False

    @staticmethod
    def _can_admin_finalize(user):
        if not user:
            return False
        return getattr(user, 'usertype', None) in ['Admin', 'Cashier']

    @staticmethod
    def doctor_approve_discharge(admission_id, doctor_user, discharge_summary=None):
        """
        Stage 1 of Inpatient Discharge: Attending Doctor authorizes clinical clearance.
        - Calculates actual days admitted (min 1 day).
        - Generates the room rent invoice (Unpaid) based on actual duration.
        - Moves admission status from 'Admitted' to 'Billing Pending'.
        - Sets discharge_approved = True and clears any pending discharge request.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return False, "Admission record not found.", None

        if not InpatientService._can_doctor_manage(doctor_user, admission):
            return False, "Access Denied: Only the attending physician or administration can approve inpatient discharge.", None

        if admission.status == 'Discharged':
            existing_bill = Billing.query.filter_by(apt_id=admission.apt_id).first()
            return False, f"Patient {admission.patient.username} is already discharged and checked out.", existing_bill

        now = datetime.now()
        delta = now - (admission.admission_date or now)
        actual_days = delta.days
        if actual_days <= 0:
            actual_days = 1 # Minimum 1 day tariff for same-day stay

        rate_per_day = Decimal(str(admission.room.rate_per_day))
        room_charge = Decimal(actual_days) * rate_per_day

        admission.status = 'Billing Pending'
        admission.actual_days = actual_days
        admission.discharge_approved = True
        admission.discharge_approved_at = now
        admission.discharge_requested = False
        admission.discharge_rejection_reason = None
        if discharge_summary:
            admission.discharge_summary = discharge_summary.strip()

        # Generate or update the room rent billing invoice
        bill = Billing.query.filter_by(apt_id=admission.apt_id).first()
        if bill:
            bill.amount = room_charge
            bill.status = 'Unpaid'
            bill.paid_on = None
            bill.payment_mode = None
            bill.transaction_ref = None
            bill.settled_by = None
        else:
            bill = Billing(
                apt_id=admission.apt_id,
                user_id=admission.patient_id,
                amount=room_charge,
                status='Unpaid'
            )
            db.session.add(bill)

        # Record clinical audit log
        doc_name = doctor_user.username if doctor_user else 'Attending Physician'
        audit = AuditLog(
            apt_id=admission.apt_id,
            user_id=admission.patient_id,
            action=f"CLINICAL DISCHARGE APPROVED by Dr. {doc_name} (Stay: {actual_days} days, Room Rent: Rs.{room_charge}). Inpatient bill generated.",
            timestamp=now.strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(audit)
        db.session.commit()
        return True, f"Clinical discharge approved for {admission.patient.username}! Room fee of ₹{room_charge} generated for {actual_days} days. Patient transitioned to Billing Pending status.", bill

    @staticmethod
    def doctor_reject_discharge(admission_id, doctor_user, reason):
        """
        Attending doctor rejects a patient-initiated early discharge request with clinical justification.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return False, "Admission record not found."

        if not InpatientService._can_doctor_manage(doctor_user, admission):
            return False, "Access Denied: Only the attending physician or administration can reject early discharge."

        admission.discharge_requested = False
        rejection_note = reason.strip() if reason else "Clinical examination indicates continued monitored inpatient care is required."
        admission.discharge_rejection_reason = rejection_note

        doc_name = doctor_user.username if doctor_user else 'Attending Physician'
        audit = AuditLog(
            apt_id=admission.apt_id,
            user_id=admission.patient_id,
            action=f"EARLY DISCHARGE REJECTED by Dr. {doc_name}: {rejection_note}",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(audit)
        db.session.commit()
        return True, f"Early discharge request rejected. Patient will remain under observation. Clinical reason logged."

    @staticmethod
    def doctor_extend_stay(admission_id, doctor_user, additional_days=1, clinical_notes=None):
        """
        Attending doctor extends tentative inpatient duration when patient requires further recovery.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return False, "Admission record not found."

        if not InpatientService._can_doctor_manage(doctor_user, admission):
            return False, "Access Denied: Only the attending physician or administration can extend inpatient stay."

        days_to_add = int(additional_days or 1)
        admission.tentative_days = (admission.tentative_days or 3) + days_to_add
        if clinical_notes:
            admission.stay_extended_notes = clinical_notes.strip()

        doc_name = doctor_user.username if doctor_user else 'Attending Physician'
        audit = AuditLog(
            apt_id=admission.apt_id,
            user_id=admission.patient_id,
            action=f"STAY EXTENDED by Dr. {doc_name}: +{days_to_add} days (New tentative: {admission.tentative_days} days). Notes: {clinical_notes or 'None'}",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(audit)
        db.session.commit()
        return True, f"Inpatient stay extended by {days_to_add} days. Tentative total is now {admission.tentative_days} days."

    @staticmethod
    def admin_confirm_discharge(admission_id, admin_user):
        """
        Stage 2 of Inpatient Discharge: Admin / Cashier confirms final clearance and releases room bed.
        Enforces precondition: room rent billing invoice must be Paid.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return False, "Admission record not found."

        if not InpatientService._can_admin_finalize(admin_user):
            return False, "Access Denied: Only hospital administration or cashier can finalize discharge and release beds."

        if admission.status == 'Discharged':
            return False, f"Patient {admission.patient.username} has already completed discharge and room release."

        # Verify fee settlement
        bill = Billing.query.filter_by(apt_id=admission.apt_id).first()
        if bill and bill.status != 'Paid':
            return False, f"Cannot complete discharge: Outstanding fees of ₹{bill.amount} must be settled before bed release."

        now = datetime.now()
        admission.status = 'Discharged'
        admission.discharge_date = now

        # Free the room
        if admission.room:
            admission.room.status = 'Available'

        actor_name = admin_user.username if admin_user else 'Hospital Staff'
        audit = AuditLog(
            apt_id=admission.apt_id,
            user_id=admission.patient_id,
            action=f"FINAL DISCHARGE & BED RELEASE CONFIRMED by {actor_name} (Room {admission.room.room_number} Available)",
            timestamp=now.strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(audit)
        db.session.commit()
        return True, f"Discharge finalized! Room {admission.room.room_number} ({admission.room.ward_type} Ward) released successfully."

    @staticmethod
    def request_discharge(admission_id, patient_user, notes=None):
        """
        Patient-initiated request for early discharge review.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return False, "Admission record not found."
        
        if admission.patient_id != patient_user.id:
            return False, "Access Denied: You cannot request discharge for another patient."
            
        if admission.status == 'Discharged':
            return False, "You are already discharged from this inpatient stay."

        if admission.status == 'Billing Pending':
            return False, "Your doctor has already approved your discharge. Please settle your bill to confirm checkout."
            
        admission.discharge_requested = True
        admission.discharge_requested_at = datetime.now()
        admission.discharge_rejection_reason = None
        if notes:
            admission.discharge_notes = notes.strip()
            
        audit = AuditLog(
            apt_id=admission.apt_id,
            user_id=patient_user.id,
            action=f"DISCHARGE REQUESTED by Patient {patient_user.username} (Room: {admission.room.room_number})",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(audit)
        db.session.commit()
        return True, "Your early discharge request has been submitted to your attending medical team. Clearance rounds will be conducted shortly."

    @staticmethod
    def get_or_create_interim_bill(admission_id):
        """
        Retrieves or generates the room rent invoice for an inpatient admission.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return None
            
        bill = Billing.query.filter_by(apt_id=admission.apt_id).first()
        if bill:
            if admission.status == 'Billing Pending' and admission.actual_days:
                bill.amount = Decimal(admission.actual_days) * Decimal(str(admission.room.rate_per_day))
                db.session.commit()
            return bill

        now = datetime.now()
        delta = now - (admission.admission_date or now)
        days = max(1, delta.days)
        rate_per_day = Decimal(str(admission.room.rate_per_day))
        total_amount = Decimal(days) * rate_per_day
        
        bill = Billing(
            apt_id=admission.apt_id,
            user_id=admission.patient_id,
            amount=total_amount,
            status='Unpaid'
        )
        db.session.add(bill)
        db.session.commit()
        return bill

    @staticmethod
    def discharge_patient(admission_id, actor=None, discharge_summary=None):
        """
        Unified discharge bridge:
        Maintains complete compatibility with automated test suite and legacy callers.
        If called directly, calculates actual duration, generates bill, and completes discharge.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return False, "Admission record not found.", None

        if admission.status == 'Discharged':
            existing_bill = Billing.query.filter_by(apt_id=admission.apt_id).first()
            return False, f"Patient {admission.patient.username} is already discharged.", existing_bill

        now = datetime.now()
        admission.status = 'Discharged'
        admission.discharge_date = now
        admission.discharge_requested = False
        if discharge_summary:
            admission.discharge_summary = discharge_summary

        delta = now - (admission.admission_date or now)
        days = delta.days
        if days <= 0:
            days = 1

        rate_per_day = Decimal(str(admission.room.rate_per_day))
        room_charge = Decimal(days) * rate_per_day
        consultation_fee = Decimal('500.00')
        total_bill_amount = consultation_fee + room_charge

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

        if admission.room:
            admission.room.status = 'Available'

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
