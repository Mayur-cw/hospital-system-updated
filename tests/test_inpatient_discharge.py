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
