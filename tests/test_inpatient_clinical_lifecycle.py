import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from models import db, Admission, Billing, Room, User, Doctors
from services.inpatient import InpatientService

def test_t_inpatient_full_lifecycle(app_no_csrf):
    """
    Validates end-to-end multi-stage inpatient workflow:
    1. Admission with tentative_days.
    2. Patient early discharge request.
    3. Doctor rejects early discharge with clinical rationale.
    4. Doctor extends stay with clinical notes.
    5. Doctor approves discharge -> Status becomes 'Billing Pending' (Bed remains Occupied).
    6. Inpatient room bill is generated for actual stay days.
    7. Patient / Cashier settles the bill -> Bill becomes 'Paid'.
    8. Admin confirms discharge -> Bed released ('Available'), status becomes 'Discharged'.
    """
    with app_no_csrf.app_context():
        # Setup: doctor, patient, room
        doc_user = User.query.get(2) # Dr. First
        doctor = Doctors.query.filter_by(user_id=doc_user.id).first()
        patient_user = User.query.get(4) # Patient One
        admin_user = User.query.get(1) # Admin
        room = Room.query.get(1) # Room 101, General, 800/day
        room.status = 'Occupied'

        # 1. Create admission with tentative 3 days
        three_days_ago = datetime.now() - timedelta(days=3)
        admission = Admission(
            apt_id=1,
            patient_id=patient_user.id,
            doctor_id=doctor.did,
            room_id=room.room_id,
            admission_date=three_days_ago,
            tentative_days=3,
            status='Admitted'
        )
        db.session.add(admission)
        db.session.commit()

        assert admission.tentative_days == 3
        assert admission.status == 'Admitted'
        assert admission.discharge_approved is False

        # 2. Patient requests early discharge
        ok, msg = InpatientService.request_discharge(
            admission.admission_id,
            patient_user,
            notes="Feeling much better after 2 days"
        )
        assert ok is True
        assert admission.discharge_requested is True
        assert admission.discharge_notes == "Feeling much better after 2 days"

        # 3. Doctor evaluates and rejects early discharge for safety
        rej_ok, rej_msg = InpatientService.doctor_reject_discharge(
            admission.admission_id,
            doc_user,
            reason="WBC counts still elevated; complete 24h IV antibiotic course first."
        )
        assert rej_ok is True
        assert admission.discharge_requested is False
        assert admission.discharge_rejection_reason == "WBC counts still elevated; complete 24h IV antibiotic course first."

        # 4. Doctor extends stay by 2 days
        ext_ok, ext_msg = InpatientService.doctor_extend_stay(
            admission.admission_id,
            doc_user,
            additional_days=2,
            clinical_notes="Observation required following antibiotic course"
        )
        assert ext_ok is True
        assert admission.tentative_days == 5 # 3 + 2
        assert "Observation required" in admission.stay_extended_notes

        # 5. Doctor approves discharge
        appr_ok, appr_msg, bill = InpatientService.doctor_approve_discharge(
            admission.admission_id,
            doc_user,
            discharge_summary="Clinically stable. Vitals normal. Cleared for discharge."
        )
        assert appr_ok is True
        assert admission.status == 'Billing Pending'
        assert admission.discharge_approved is True
        assert admission.discharge_summary == "Clinically stable. Vitals normal. Cleared for discharge."
        # Room must STILL be occupied until admin confirms after bill settlement!
        assert room.status == 'Occupied'

        # 6. Room bill generated for actual days (3 days * 800 = 2400)
        assert bill is not None
        assert bill.status == 'Unpaid'
        assert bill.amount == Decimal('2400.00')

        # 7. Settle bill
        bill.status = 'Paid'
        db.session.commit()

        # 8. Admin confirms discharge and releases bed
        conf_ok, conf_msg = InpatientService.admin_confirm_discharge(
            admission.admission_id,
            admin_user
        )
        assert conf_ok is True
        assert admission.status == 'Discharged'
        assert admission.discharge_date is not None
        assert room.status == 'Available'


def test_t_inpatient_auth_isolation(app_no_csrf):
    """
    Verifies that unauthorized actors cannot approve, reject, or request discharge.
    """
    with app_no_csrf.app_context():
        # Setup admission assigned to doctor_id=1, patient_id=4
        doc_owner = User.query.get(2)
        doc_other = User.query.get(3) # Unrelated doctor
        patient_owner = User.query.get(4)
        patient_other = User.query.get(1) # Admin or different user

        room = Room.query.get(2)
        room.status = 'Occupied'

        adm = Admission(
            apt_id=11,
            patient_id=patient_owner.id,
            doctor_id=1,
            room_id=room.room_id,
            admission_date=datetime.now() - timedelta(days=1),
            tentative_days=2,
            status='Admitted'
        )
        db.session.add(adm)
        db.session.commit()

        # Unrelated patient cannot request discharge
        bad_req, _ = InpatientService.request_discharge(adm.admission_id, patient_other, "Let me out")
        assert bad_req is False

        # Unrelated doctor cannot reject or approve
        bad_rej, _ = InpatientService.doctor_reject_discharge(adm.admission_id, doc_other, "No")
        assert bad_rej is False

        bad_appr, _, _ = InpatientService.doctor_approve_discharge(adm.admission_id, doc_other, "Approve")
        assert bad_appr is False

        # Non-admin cannot confirm discharge
        bad_conf, _ = InpatientService.admin_confirm_discharge(adm.admission_id, doc_owner)
        assert bad_conf is False
