import pytest
from flask import url_for
from models import Appointments, Billing, Admission, Room

def test_t_auth_001_patient_cannot_view_others_invoice(client_no_csrf):
    """T-AUTH-001: Patient cannot view another patient's invoice by numeric ID."""
    # Login as Patient 1 (owns bill 1)
    client_no_csrf.post('/login', data={'email': 'p1@test.local', 'password': 'Pass@123'})

    # Try to access bill 2 (owned by Patient 2)
    response = client_no_csrf.get('/bills/2/invoice', follow_redirects=False)
    # Must redirect away with security denial
    assert response.status_code == 302
    assert '/my_bills' in response.headers['Location']

def test_t_auth_002_doctor_cannot_mark_other_doctor_appointment(client_no_csrf, app_no_csrf):
    """T-AUTH-002: Doctor cannot mark another doctor's appointment as Attended or Missed."""
    # Login as Dr. Second (doc2@test.local)
    client_no_csrf.post('/login', data={'email': 'doc2@test.local', 'password': 'Pass@123'})

    # Attempt to mark appointment 1 (assigned to Dr. First) as Attended
    response = client_no_csrf.post('/mark_attended/1', follow_redirects=True)
    
    # Verify appointment 1 remained 'Scheduled' in database
    with app_no_csrf.app_context():
        apt = Appointments.query.get(1)
        assert apt.slot == 'Scheduled'

    # Attempt to mark appointment 1 as Missed
    response = client_no_csrf.post('/mark_missed/1', follow_redirects=True)
    with app_no_csrf.app_context():
        apt = Appointments.query.get(1)
        assert apt.slot == 'Scheduled'

def test_t_auth_003_doctor_cannot_add_chart_to_unassigned_encounter(client_no_csrf, app_no_csrf):
    """T-AUTH-003: Doctor cannot add clinical note to another doctor's appointment."""
    # Login as Dr. Second
    client_no_csrf.post('/login', data={'email': 'doc2@test.local', 'password': 'Pass@123'})

    # Attempt to add record to appointment 1 (assigned to Dr. First)
    response = client_no_csrf.post(
        '/add_record/1',
        data={
            'diagnosis': 'Malicious cross-provider note',
            'prescription': 'None',
            'notes': 'Attacking chart'
        },
        follow_redirects=True
    )

    with app_no_csrf.app_context():
        apt = Appointments.query.get(1)
        assert apt.medical_record is None
        assert apt.slot == 'Scheduled'

def test_t_auth_004_doctor_cannot_discharge_unrelated_admission(client_no_csrf, app_no_csrf):
    """T-AUTH-004: Doctor cannot discharge an admission managed by another physician."""
    with app_no_csrf.app_context():
        adm = Admission(
            admission_id=99,
            apt_id=1,
            patient_id=4,
            doctor_id=1, # Dr. First (did 1)
            room_id=1,
            status='Admitted'
        )
        Room.query.get(1).status = 'Occupied'
        from models import db
        db.session.add(adm)
        db.session.commit()

    # Login as Dr. Second (did 2)
    client_no_csrf.post('/login', data={'email': 'doc2@test.local', 'password': 'Pass@123'})

    # Attempt to discharge admission 99
    response = client_no_csrf.post('/discharge_patient', data={'admission_id': 99}, follow_redirects=True)

    with app_no_csrf.app_context():
        adm_check = Admission.query.get(99)
        assert adm_check.status == 'Admitted'
        assert adm_check.discharge_date is None

def test_t_auth_005_doctor_cannot_view_unrelated_booking_success(client_no_csrf):
    """T-AUTH-005: Doctor cannot view booking success page for another doctor's appointment."""
    # Login as Dr. Second
    client_no_csrf.post('/login', data={'email': 'doc2@test.local', 'password': 'Pass@123'})

    # Attempt to view booking success for appointment 1 (assigned to Dr. First and Patient 1)
    response = client_no_csrf.get('/booking_success/1', follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/')
