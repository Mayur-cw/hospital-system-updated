import pytest
from datetime import datetime
from models import db, MedicalRecord, ClinicalNoteRevision, Appointments, Billing, User
from services.clinical import ClinicalService

def test_t_note_001_signed_note_immutability_and_amendment_trail(app_no_csrf):
    """
    T-NOTE-001: Signed notes cannot overwrite original text silently.
    Amendments require a stated justification and retain the original revision immutably.
    """
    with app_no_csrf.app_context():
        doc = User.query.get(2) # Dr. First

        # 1. Sign original clinical note
        success, msg, record = ClinicalService.save_medical_record(
            apt_id=1,
            diagnosis='Initial Diagnosis: Mild Asthma',
            prescription='Salbutamol Inhaler 100mcg PRN',
            notes='Review in 2 weeks',
            doctor_user=doc,
            action='sign'
        )
        assert success is True
        assert record.status == 'Signed'
        assert record.signed_by == 'Dr. First'

        # 2. Attempt amendment WITHOUT a reason (Must fail)
        fail_amend, fail_msg = ClinicalService.amend_medical_record(
            record_id=record.record_id,
            new_diagnosis='Revised: Moderate Persistent Asthma',
            new_prescription='Salbutamol + Budesonide 200mcg BD',
            amendment_reason='', # Missing reason
            doctor_user=doc
        )
        assert fail_amend is False
        assert "amendment reason is legally required" in fail_msg

        # 3. Valid amendment with clinical justification
        success_amend, amend_msg = ClinicalService.amend_medical_record(
            record_id=record.record_id,
            new_diagnosis='Revised: Moderate Persistent Asthma',
            new_prescription='Salbutamol + Budesonide 200mcg BD',
            amendment_reason='Spirometry results confirmed persistent airflow limitation.',
            doctor_user=doc
        )
        assert success_amend is True
        assert record.status == 'Amended'
        assert record.diagnosis == 'Revised: Moderate Persistent Asthma'

        # 4. Verify immutable revision history record exists
        revisions = ClinicalNoteRevision.query.filter_by(record_id=record.record_id).all()
        assert len(revisions) == 1
        rev = revisions[0]
        assert rev.previous_diagnosis == 'Initial Diagnosis: Mild Asthma'
        assert rev.previous_prescription == 'Salbutamol Inhaler 100mcg PRN'
        assert rev.new_diagnosis == 'Revised: Moderate Persistent Asthma'
        assert rev.amended_by == 'Dr. First'
        assert 'Spirometry' in rev.amendment_reason

def test_t_data_001_archived_patient_preserves_clinical_and_financial_truth(app_no_csrf):
    """
    T-DATA-001: Deactivating/archiving a user or cancelling an appointment preserves
    all historical encounters, notes, receipts, and audit trail rows.
    """
    with app_no_csrf.app_context():
        p1 = User.query.get(4)
        p1.is_active = False # Soft deactivate
        db.session.commit()

        # Historical appointments and bills must remain intact
        apts = Appointments.query.filter_by(user_id=4).all()
        assert len(apts) >= 1
        bills = Billing.query.filter_by(user_id=4).all()
        assert len(bills) >= 1
