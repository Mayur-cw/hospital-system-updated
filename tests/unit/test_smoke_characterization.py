import pytest
from datetime import date
from flask import url_for
from models import db, User, Appointments, MedicalRecord, Billing, Admission, Room, Doctors

def test_char_auth_signup_and_login_success(client, app):
    """Pin baseline patient signup and authentication flow."""
    # 1. Signup new patient
    signup_resp = client.post('/signup', data={
        'username': 'Neelam Verma',
        'email': 'neelam@test.local',
        'password': 'SecurePassword@123',
        'phone': '555-0205',
        'gender': 'Female'
    }, follow_redirects=True)
    assert signup_resp.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email='neelam@test.local').first()
        assert user is not None
        assert user.usertype == 'Patient'

    # 2. Login as the newly created patient
    login_resp = client.post('/login', data={
        'email': 'neelam@test.local',
        'password': 'SecurePassword@123'
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    assert b"Login successful!" in login_resp.data

def test_char_auth_invalid_credentials(client):
    """Pin baseline rejected authentication response."""
    resp = client.post('/login', data={
        'email': 'p1@test.local',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Invalid email or password" in resp.data

@pytest.mark.xfail(strict=True, reason="Legacy booking calls MySQL procedure BookAppointmentSafe which is unavailable in SQLite characterization tests")
def test_char_booking_scheduled(client, app):
    """Pin baseline appointment booking creation."""
    client.post('/login', data={'email': 'p1@test.local', 'password': 'PatientPass@123'}, follow_redirects=True)
    resp = client.post('/patients', data={
        'slot': 'Scheduled',
        'email': 'p1@test.local',
        'name': 'Patient One',
        'gender': 'Male',
        'phone': '555-0201',
        'disease': 'Skin Rash',
        'date': '2026-12-01',
        'time': '11:00 AM',
        'dept': 'Dermatologists',
        'doctor': 'Dr. Patel'
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        apt = Appointments.query.filter_by(disease='Skin Rash').first()
        assert apt is not None
        assert apt.doctor == 'Dr. Patel'
        assert apt.slot == 'Scheduled'

def test_char_doctor_queue_and_checkin(client, app):
    """Pin baseline doctor viewing and marking appointment attended."""
    client.post('/login', data={'email': 'doc1@test.local', 'password': 'DoctorPass@123'}, follow_redirects=True)
    resp = client.post('/mark_attended/1', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        apt = db.session.get(Appointments, 1)
        assert apt.slot == 'Attended'

def test_char_doctor_create_medical_record(client, app):
    """Pin baseline clinical note generation."""
    client.post('/login', data={'email': 'doc1@test.local', 'password': 'DoctorPass@123'}, follow_redirects=True)
    resp = client.post('/add_record/1', data={
        'diagnosis': 'Stage 1 Essential Hypertension',
        'prescription': 'Amlodipine 5mg OD PO',
        'notes': 'Follow up in 2 weeks with BP diary.'
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        rec = MedicalRecord.query.filter_by(apt_id=1).first()
        assert rec is not None
        assert "Amlodipine" in rec.prescription

# ─────────────────────────────────────────────────────────────────────────────
# Characterization Tests for Known Phase 1 Bugs (pinned with xfail)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.xfail(strict=True, reason="B-10: get_booked_slots crashes with AttributeError when body is null/non-dict JSON")
def test_char_b10_get_booked_slots_crash(client):
    """B-10: POST to /get_booked_slots with null JSON body crashes with AttributeError."""
    client.post('/login', data={'email': 'p1@test.local', 'password': 'PatientPass@123'}, follow_redirects=True)
    resp = client.post('/get_booked_slots', data='null', content_type='application/json')
    assert resp.status_code == 200

@pytest.mark.xfail(strict=True, reason="B-08: patient.py compares str with datetime.date object (always evaluates False)")
def test_char_b08_date_comparison_inconsistency(app):
    """B-08: SQLAlchemy models.py String(50) date compared with datetime.date object."""
    with app.app_context():
        apt = db.session.get(Appointments, 1)
        today = date.today()
        # In patient.py:160, 'if apt.date == today' is executed.
        # This asserts what patient.py intends: that apt.date matches today's date
        assert apt.date == today  # FAILS because str != date in Python!

@pytest.mark.xfail(strict=True, reason="B-06: admin discharge does not create billing record")
def test_char_b06_two_discharge_flows_discrepancy(client, app):
    """B-06: Admin discharge marks room available but fails to generate billing invoice."""
    with app.app_context():
        adm = Admission(
            admission_id=1, apt_id=1, patient_id=4, doctor_id=1, room_id=1, status='Admitted'
        )
        db.session.get(Room, 1).status = 'Occupied'
        db.session.add(adm)
        db.session.commit()

    # Login as Admin and perform admin discharge
    client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'}, follow_redirects=True)
    resp = client.post('/admin/discharge/1', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        # Once consolidated, an invoice MUST be generated. Today admin discharge never creates an invoice.
        bill = Billing.query.filter_by(apt_id=1).first()
        assert bill is not None  # FAILS on legacy code!

def test_char_b01_add_staff_form_and_creation(client, app):
    """B-01: Forms in base.html and admin templates post to /admin/add_staff and create user + doctor."""
    client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'}, follow_redirects=True)
    resp_page = client.get('/admin/doctors')
    assert b'action="/admin/add_staff"' in resp_page.data
    assert b'action="/add_staff"' not in resp_page.data

    resp = client.post('/admin/add_staff', data={
        'username': 'Dr. New', 'usertype': 'Doctor', 'email': 'newdoc@test.local',
        'password': 'Pass@123', 'dept': 'Neurology'
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        u = User.query.filter_by(email='newdoc@test.local').first()
        assert u is not None
        assert u.usertype == 'Doctor'
        d = Doctors.query.filter_by(user_id=u.id).first()
        assert d is not None
        assert d.dept == 'Neurology'

def test_char_b03_admin_dashboard_link_valid(client):
    """B-03: Breadcrumb links navigate to /admin/dashboard, not 404 targets /admin or /admin_dashboard."""
    client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'}, follow_redirects=True)
    for path in ['/admin/patients', '/admin/doctors', '/admin/staff', '/admin/appointments']:
        resp = client.get(path)
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'href="/admin_dashboard"' not in html
        assert 'href="/admin"' not in html
        assert 'href="/admin/dashboard"' in html

def test_char_b04_admin_view_invoice_missing_template(client, app):
    """B-04: admin.view_invoice successfully renders admin_view_invoice.html."""
    with app.app_context():
        b = Billing(bill_id=1, apt_id=1, user_id=4, amount=500.00, status='Unpaid')
        db.session.add(b)
        db.session.commit()

    client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'}, follow_redirects=True)
    resp = client.get('/admin/financials/1/invoice', follow_redirects=False)
    assert resp.status_code == 200
    assert b"Invoice" in resp.data

def test_char_b24_toast_dismiss_button_has_alert_class(client):
    """B-24: base.html flash toast element includes .alert class for Bootstrap data-bs-dismiss='alert'."""
    resp = client.post('/login', data={'email': 'p1@test.local', 'password': 'WrongPassword'}, follow_redirects=True)
    html = resp.data.decode('utf-8')
    assert 'class="toast-alert alert' in html
