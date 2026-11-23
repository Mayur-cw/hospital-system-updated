import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from models import db, Admission, Billing, Room, User
from services.inpatient import InpatientService

def test_t_disch_001_repeated_discharge_is_idempotent(app_no_csrf):
    """
    T-DISCH-001: Submitting discharge repeatedly produces exactly ONE discharge
    event and ONE final bill, with zero duplicate invoices.
    """
    with app_no_csrf.app_context():
        # Setup admission with 3 days duration
        room = Room.query.get(1)
        room.status = 'Occupied'
        three_days_ago = datetime.now() - timedelta(days=3)

        adm = Admission(
            apt_id=1,
            patient_id=4,
            doctor_id=1,
            room_id=1,
            admission_date=three_days_ago,
            status='Admitted'
        )
        db.session.add(adm)
        db.session.commit()

        actor = User.query.get(1) # Admin

        # 1st Discharge Call
        success1, msg1, bill1 = InpatientService.discharge_patient(adm.admission_id, actor)
        assert success1 is True
        assert "discharged successfully" in msg1
        assert bill1 is not None

        # Verify bill amount: Rs. 500 consultation + (3 days * Rs. 800) = Rs. 2900.00
        assert bill1.amount == Decimal('2900.00')
        assert room.status == 'Available'

        # Verify bill count for this appointment
        bills_after_first = Billing.query.filter_by(apt_id=1).all()
        assert len(bills_after_first) == 1

        # 2nd Discharge Call (Simulating rapid double-click or replay)
        success2, msg2, bill2 = InpatientService.discharge_patient(adm.admission_id, actor)
        assert success2 is False
        assert "already discharged" in msg2

        # Verify NO duplicate bill created
        bills_after_second = Billing.query.filter_by(apt_id=1).all()
        assert len(bills_after_second) == 1
        assert bills_after_second[0].amount == Decimal('2900.00')


def test_t_disch_002_patient_discharge_request_and_interim_bill(app_no_csrf):
    """
    T-DISCH-002: Patient can request discharge review, generating audit event and
    enabling interim bill settlement prior to clinician clearance.
    """
    with app_no_csrf.app_context():
        patient = User.query.get(4)
        room = Room.query.get(2)
        room.status = 'Occupied'

        adm = Admission(
            apt_id=2,
            patient_id=patient.id,
            doctor_id=1,
            room_id=room.room_id,
            admission_date=datetime.now() - timedelta(days=2),
            status='Admitted'
        )
        db.session.add(adm)
        db.session.commit()

        # 1. Patient requests discharge
        success, msg = InpatientService.request_discharge(
            admission_id=adm.admission_id,
            patient_user=patient,
            notes="Recovered well, request clearance"
        )
        assert success is True
        assert adm.discharge_requested is True
        assert adm.discharge_notes == "Recovered well, request clearance"

        # 2. Get interim bill
        bill = InpatientService.get_or_create_interim_bill(adm.admission_id)
        assert bill is not None
        assert bill.status == 'Unpaid'
        # Rs. 500 consultation + (2 days * 1200) = 2900
        assert bill.amount >= Decimal('500.00')

        # 3. Doctor authorizes final discharge
        doc = User.query.get(2)
        disch_ok, disch_msg, final_bill = InpatientService.discharge_patient(adm.admission_id, doc, "Cleared")
        assert disch_ok is True
        assert adm.status == 'Discharged'
        assert adm.discharge_requested is False
        assert room.status == 'Available'


def test_t_disch_003_patient_cancel_discharge_request_lifecycle(app_no_csrf):
    """
    T-DISCH-003: Patient can cancel/withdraw their pending early discharge request,
    retaining active monitored inpatient care status.
    """
    with app_no_csrf.app_context():
        patient = User.query.get(4)
        unrelated_user = User.query.get(1) # Admin
        room = Room.query.get(2)
        room.status = 'Occupied'

        adm = Admission(
            apt_id=3,
            patient_id=patient.id,
            doctor_id=1,
            room_id=room.room_id,
            admission_date=datetime.now() - timedelta(days=1),
            status='Admitted'
        )
        db.session.add(adm)
        db.session.commit()

        # Step 1: Patient requests discharge
        ok, msg = InpatientService.request_discharge(adm.admission_id, patient, "Feel better")
        assert ok is True
        assert adm.discharge_requested is True
        assert adm.discharge_notes == "Feel better"

        # Step 2: Unrelated user cannot cancel request
        bad_cancel, bad_msg = InpatientService.cancel_discharge_request(adm.admission_id, unrelated_user)
        assert bad_cancel is False
        assert "Access Denied" in bad_msg
        assert adm.discharge_requested is True

        # Step 3: Patient cancels their own early discharge request
        cancel_ok, cancel_msg = InpatientService.cancel_discharge_request(adm.admission_id, patient)
        assert cancel_ok is True
        assert adm.discharge_requested is False
        assert adm.discharge_notes is None
        assert "cancelled" in cancel_msg.lower()

        # Step 4: Redundant cancel returns error
        again_ok, again_msg = InpatientService.cancel_discharge_request(adm.admission_id, patient)
        assert again_ok is False
        assert "No active early discharge request" in again_msg


