# tests/unit/test_authorization_matrix.py - Automated Authorization Matrix Test (T-04, S-05)

# Complete route expectation matrix mapping every endpoint to allowed roles
# Allowed roles: 'Public', 'Patient', 'Doctor', 'Admin'
ROUTE_ACCESS_MATRIX = {
    # Public & Health Endpoints
    'health.healthz': {'Public', 'Patient', 'Doctor', 'Admin'},
    'health.readyz': {'Public', 'Patient', 'Doctor', 'Admin'},
    'main.index': {'Public', 'Patient', 'Doctor', 'Admin'},
    'main.doctors': {'Public', 'Patient', 'Doctor', 'Admin'},
    'main.search': {'Public', 'Patient', 'Doctor', 'Admin'},
    'auth.login': {'Public', 'Patient', 'Doctor', 'Admin'},
    'auth.signup': {'Public', 'Patient', 'Doctor', 'Admin'},
    'auth.forgot_password': {'Public', 'Patient', 'Doctor', 'Admin'},
    'auth.reset_password': {'Public', 'Patient', 'Doctor', 'Admin'},
    'api_v1.api_docs': {'Public', 'Patient', 'Doctor', 'Admin'},
    'api_v1.openapi_spec': {'Public', 'Patient', 'Doctor', 'Admin'},
    'api_v1.get_doctor_slots': {'Public', 'Patient', 'Doctor', 'Admin'},
    'api_v1.global_search': {'Public', 'Patient', 'Doctor', 'Admin'},
    'redirect_api_docs': {'Public', 'Patient', 'Doctor', 'Admin'},

    # Authenticated Common Endpoints
    'auth.profile': {'Patient', 'Doctor', 'Admin'},
    'auth.logout': {'Patient', 'Doctor', 'Admin'},
    'api_v1.get_notifications': {'Patient', 'Doctor', 'Admin'},
    'api_v1.mark_notification_read': {'Patient', 'Doctor', 'Admin'},

    # Patient Endpoints
    'patient.dashboard': {'Patient'},
    'patient.patient_booking': {'Patient', 'Admin'},
    'patient.upcoming_bookings': {'Patient'},
    'patient.past_records': {'Patient'},
    'patient.my_bills': {'Patient'},
    'patient.view_invoice': {'Patient', 'Admin'},
    'patient.view_receipt': {'Patient', 'Admin'},
    'patient.booking_success': {'Patient'},
    'patient.cancel_appointment': {'Patient', 'Admin'},
    'patient.reschedule_appointment': {'Patient', 'Admin'},
    'patient.process_payment': {'Patient'},
    'patient.get_booked_slots': {'Patient', 'Public'},

    # Doctor Endpoints
    'doctor.view_record': {'Doctor'},
    'doctor.add_record': {'Doctor'},
    'doctor.edit_record': {'Doctor'},
    'doctor.cancel_apt': {'Doctor'},
    'doctor.mark_attended': {'Doctor'},
    'doctor.mark_missed': {'Doctor'},
    'doctor.my_admissions': {'Doctor'},
    'doctor.discharge_patient': {'Doctor'},

    # Admin Endpoints
    'admin.admin_dashboard': {'Admin'},
    'admin.admin_doctors': {'Admin'},
    'admin.admin_patients': {'Admin'},
    'admin.admin_appointments': {'Admin'},
    'admin.admin_rooms': {'Admin'},
    'admin.admin_financials': {'Admin'},
    'admin.admin_staff': {'Admin'},
    'admin.admin_settings': {'Admin'},
    'admin.details': {'Admin'},
    'admin.view_invoice': {'Admin'},
    'admin.view_receipt': {'Admin'},
    'admin.add_room': {'Admin'},
    'admin.edit_room': {'Admin'},
    'admin.delete_room': {'Admin'},
    'admin.discharge_patient': {'Admin'},
    'admin.admin_edit_doctor': {'Admin'},
    'admin.admin_delete_doctor': {'Admin'},
    'admin.admin_change_doctor_password': {'Admin'},
    'admin.add_staff': {'Admin'},
    'admin.admin_edit_staff': {'Admin'},
    'admin.admin_delete_staff': {'Admin'},
    'admin.admin_change_staff_password': {'Admin'},
    'admin.admin_update_appointment_status': {'Admin'},
    'admin.admin_delete_appointment': {'Admin'},
    'admin.export_appointments_csv': {'Admin'},
    'admin.export_invoices_csv': {'Admin'},
    'admin.export_audit_logs_csv': {'Admin'},
}


def test_t04_all_routes_registered_in_matrix(app):
    """
    T-04: Ensure every non-static route in the application has an explicit
    security authorization expectation. Fails build if a developer adds a route
    without declaring its role policy.
    """
    registered_endpoints = {
        rule.endpoint for rule in app.url_map.iter_rules()
        if not rule.endpoint.startswith('static')
    }

    missing_expectations = registered_endpoints - set(ROUTE_ACCESS_MATRIX.keys())
    assert not missing_expectations, (
        f"Security Gate Failed: The following endpoints are missing authorization expectations in ROUTE_ACCESS_MATRIX: {missing_expectations}"
    )


def test_t04_anonymous_access_boundaries(client):
    """T-04: Anonymous user can only access public routes; protected routes redirect to login."""
    # 1. Public route succeeds
    resp_pub = client.get("/")
    assert resp_pub.status_code == 200

    resp_health = client.get("/healthz")
    assert resp_health.status_code == 200

    # 2. Protected admin route redirects to login
    resp_admin = client.get("/admin/dashboard")
    assert resp_admin.status_code == 302
    assert "/login" in resp_admin.headers.get("Location", "")

    # 3. Protected patient route redirects to login
    resp_patient = client.get("/dashboard")
    assert resp_patient.status_code == 302
    assert "/login" in resp_patient.headers.get("Location", "")


def test_t04_patient_cannot_access_admin_or_doctor_routes(client):
    """T-04: Patient is strictly forbidden from accessing Admin or Doctor control planes."""
    client.post('/login', data={'email': 'p1@test.local', 'password': 'PatientPass@123'}, follow_redirects=True)

    # Attempt admin dashboard
    resp_admin = client.get("/admin/dashboard")
    assert resp_admin.status_code in (403, 302)

    # Attempt admin settings
    resp_settings = client.get("/admin/settings")
    assert resp_settings.status_code in (403, 302)

    # Attempt doctor admissions
    resp_doc = client.get("/doctor_admissions")
    assert resp_doc.status_code in (403, 302)


def test_t04_doctor_cannot_access_admin_control_plane(client):
    """T-04: Doctor cannot access administrative settings or financial control plane."""
    client.post('/login', data={'email': 'doc1@test.local', 'password': 'DoctorPass@123'}, follow_redirects=True)

    resp_admin = client.get("/admin/settings")
    assert resp_admin.status_code in (403, 302)

    resp_staff = client.get("/admin/staff")
    assert resp_staff.status_code in (403, 302)


def test_t04_admin_can_access_admin_routes(client):
    """T-04: Admin has authorized access to admin dashboard and settings."""
    client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'}, follow_redirects=True)

    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200

    resp_settings = client.get("/admin/settings")
    assert resp_settings.status_code == 200
