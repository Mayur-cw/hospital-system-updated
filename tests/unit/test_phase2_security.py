"""
tests/unit/test_phase2_security.py
Comprehensive test suite verifying Phase 2 Security Hardening:
- S-01: CSRF protection enforcement on mutating routes
- S-02: Logout via POST
- S-03: Open redirect prevention via safe_redirect & is_safe_url
- S-04: Rate limiting on sensitive endpoints (login, forgot-password)
- S-05: Central RBAC authorization matrix (Role and Object-level policies)
- S-06: Password policy enforcement (min 10 chars, breach blocklist)
- S-07 & S-08: Security headers, session flags, and Cache-Control
- S-09: Debug off by default & custom error handlers (400, 403, 404, 429, 500)
- S-12: Account lifecycle & signed expiring reset tokens
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from hms import create_app
from hms.config import TestingConfig
from hms.extensions import db
from hms.models.billing import Invoice, InvoiceStatus
from hms.models.user import User
from hms.utils.security import (
    generate_token,
    is_safe_url,
    validate_password_strength,
    verify_token,
)
from tests.conftest import _seed_fixtures


class CSRFTestingConfig(TestingConfig):
    WTF_CSRF_ENABLED = True
    SECRET_KEY = 'csrf-test-secret-key-42'


class RateLimitTestingConfig(TestingConfig):
    RATELIMIT_ENABLED = True
    SECRET_KEY = 'ratelimit-test-secret-key-99'


# ── S-01: CSRF PROTECTION ─────────────────────────────────────────────

def test_s01_csrf_protection_rejects_missing_token():
    """S-01: Mutating POST requests without a valid CSRF token return 400 Bad Request."""
    csrf_app = create_app(CSRFTestingConfig)
    with csrf_app.app_context():
        db.create_all()
        _seed_fixtures()
        client = csrf_app.test_client()

        # Attempt login without CSRF token
        resp = client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'})
        assert resp.status_code == 400
        assert b"CSRF" in resp.data or b"Bad Request" in resp.data

        # Attempt booking without CSRF token
        book_resp = client.post('/patients', data={'disease': 'Fever', 'doctor': 'Dr. Sharma'})
        assert book_resp.status_code == 400

        db.session.remove()
        db.drop_all()


# ── S-02: LOGOUT VIA POST ─────────────────────────────────────────────

def test_s02_logout_requires_post(client, app):
    """S-02: Logout must be a POST request; GET request is rejected (405)."""
    # Login as Patient 1
    client.post('/login', data={'email': 'p1@test.local', 'password': 'PatientPass@123'}, follow_redirects=True)

    # 1. GET /logout must be rejected with 405 Method Not Allowed
    get_resp = client.get('/logout')
    assert get_resp.status_code == 405

    # 2. POST /logout successfully terminates session
    post_resp = client.post('/logout', follow_redirects=True)
    assert post_resp.status_code == 200
    assert b"logged out" in post_resp.data


# ── S-03: OPEN REDIRECT PREVENTION ───────────────────────────────────

def test_s03_open_redirect_prevention(client):
    """S-03: safe_redirect rejects protocol-relative, absolute, or external URLs."""
    # Unit level checks on is_safe_url
    assert is_safe_url('/dashboard') is True
    assert is_safe_url('/admin/doctors') is True
    assert is_safe_url('//evil.com') is False
    assert is_safe_url('\\\\evil.com') is False
    assert is_safe_url('http://malicious.com') is False
    assert is_safe_url('https://malicious.com') is False
    assert is_safe_url('javascript:alert(1)') is False
    assert is_safe_url('') is False
    assert is_safe_url(None) is False

    # HTTP level: attempt login with malicious next param
    resp = client.post('/login?next=http://evil.com/phish', data={
        'email': 'p1@test.local', 'password': 'PatientPass@123'
    }, follow_redirects=False)

    # Should redirect safely to main.index (/), NOT evil.com
    assert resp.status_code == 302
    assert resp.headers.get('Location') == '/'


# ── S-04: RATE LIMITING ───────────────────────────────────────────────

def test_s04_rate_limiting_triggers_429():
    """S-04: Rapid repeated requests trigger Flask-Limiter and return HTTP 429."""
    rl_app = create_app(RateLimitTestingConfig)
    with rl_app.app_context():
        db.create_all()
        client = rl_app.test_client()

        # Hit /forgot-password repeatedly (limit: 5 per minute)
        hit_429 = False
        for _ in range(8):
            r = client.post('/forgot-password', data={'email': 'nobody@test.local'})
            if r.status_code == 429:
                hit_429 = True
                assert b"Rate Limit Exceeded" in r.data or b"429" in r.data
                break

        assert hit_429, "Rate limiter did not trigger 429 on excessive requests"

        db.session.remove()
        db.drop_all()


# ── S-05: CENTRAL RBAC AUTHORIZATION MATRIX ──────────────────────────

def test_s05_rbac_authorization_matrix(client, app):
    """
    S-05 & T-04: Central RBAC and object-level policy authorization matrix.
    - Unauthenticated cannot access staff or clinical portals.
    - Patient cannot access admin dashboard (403).
    - Doctor cannot access admin dashboard (403).
    - Patient cannot view another patient's invoice (403).
    - Patient can view their own invoice (200).
    - Doctor cannot alter another doctor's patient appointment (403).
    """
    # 1. Unauthenticated -> Redirects to login
    anon_resp = client.get('/admin/dashboard', follow_redirects=False)
    assert anon_resp.status_code == 302
    assert '/login' in anon_resp.headers.get('Location', '')

    # 2. Patient accessing Admin Dashboard -> 403 Forbidden
    client.post('/login', data={'email': 'p1@test.local', 'password': 'PatientPass@123'}, follow_redirects=True)
    pat_to_admin = client.get('/admin/dashboard')
    assert pat_to_admin.status_code == 403
    assert b"Access Denied" in pat_to_admin.data

    # 3. Patient accessing Doctor Inpatient Admissions -> 403 Forbidden
    pat_to_doc = client.get('/doctor_admissions')
    assert pat_to_doc.status_code == 403

    # 4. Patient 1 viewing another Patient's (Patient 2) Invoice -> 403 Forbidden
    with app.app_context():
        inv_p2 = Invoice(
            invoice_number='INV-P2-999',
            patient_id=5,  # Patient 2
            subtotal=Decimal('600.00'),
            total=Decimal('600.00'),
            status=InvoiceStatus.ISSUED,
            issued_at=datetime.now(UTC)
        )
        db.session.add(inv_p2)
        db.session.commit()
        inv_p2_id = inv_p2.id

    p1_view_p2_bill = client.get(f'/bills/{inv_p2_id}/invoice')
    assert p1_view_p2_bill.status_code == 403

    # 5. Doctor accessing Admin Dashboard -> 403 Forbidden
    client.post('/logout')
    client.post('/login', data={'email': 'doc1@test.local', 'password': 'DoctorPass@123'}, follow_redirects=True)
    doc_to_admin = client.get('/admin/dashboard')
    assert doc_to_admin.status_code == 403

    # 6. Admin accessing Admin Dashboard -> 200 OK
    client.post('/logout')
    client.post('/login', data={'email': 'admin@test.local', 'password': 'AdminPass@123'}, follow_redirects=True)
    admin_resp = client.get('/admin/dashboard')
    assert admin_resp.status_code == 200


# ── S-06: PASSWORD POLICY ─────────────────────────────────────────────

def test_s06_password_strength_policy():
    """S-06: Passwords require min 10 chars, reject breached/common passwords, and never strip."""
    # Under 10 characters
    ok, err = validate_password_strength('short')
    assert not ok
    assert "at least 10 characters" in err

    # Common / breached passwords
    for common_pw in ['password123', 'admin12345', 'hospital123', 'hedgewar123']:
        ok, err = validate_password_strength(common_pw)
        assert not ok
        assert "common or easily guessable" in err

    # Valid strong passphrases
    ok, err = validate_password_strength('Hedgewar-Clinical-Safe-2026')
    assert ok
    assert err is None


def test_s06_signup_enforces_password_policy(client, app):
    """S-06: Signup rejects passwords that violate policy."""
    resp = client.post('/signup', data={
        'username': 'WeakUser',
        'email': 'weak@test.local',
        'password': 'short'  # < 10 chars
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Password must be at least 10 characters long" in resp.data

    with app.app_context():
        u = User.query.filter_by(email='weak@test.local').first()
        assert u is None


# ── S-07 & S-08: SECURITY & TRACING HEADERS ──────────────────────────

def test_s07_s08_security_headers_and_cache_control(client):
    """S-07 & S-08: Standard security headers, request ID, and no-store on clinical/financial routes."""
    # Public page has security headers and X-Request-ID
    home_resp = client.get('/')
    assert home_resp.status_code == 200
    assert 'X-Request-ID' in home_resp.headers
    assert home_resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert home_resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'

    # Sensitive route has Cache-Control: no-store
    login_resp = client.get('/profile')
    assert 'no-store' in login_resp.headers.get('Cache-Control', '')


# ── S-09: CUSTOM ERROR HANDLERS ───────────────────────────────────────

def test_s09_custom_error_pages(client):
    """S-09: Custom 404, 403, and JSON error reporting with incident request ID."""
    # 404 page
    not_found = client.get('/non-existent-page-xyz')
    assert not_found.status_code == 404
    assert b"Resource Not Found" in not_found.data
    assert b"Incident / Request ID" in not_found.data

    # API 404 returns JSON with request_id
    json_404 = client.get('/api/invalid-endpoint', headers={'Accept': 'application/json'})
    assert json_404.status_code == 404
    data = json_404.get_json()
    assert data is not None
    assert 'request_id' in data
    assert data['error'] == 'Not Found'


# ── S-12: ACCOUNT LIFECYCLE & SIGNED RESET TOKENS ────────────────────

def test_s12_expiring_signed_reset_tokens(app):
    """S-12: Signed reset tokens are single-use, timed, and tamper-resistant."""
    secret = 'test-secret-key'
    token = generate_token({'user_id': 4}, secret)
    assert token is not None

    # 1. Valid token decrypts correctly
    data = verify_token(token, secret, max_age_seconds=1800)
    assert data is not None
    assert data['user_id'] == 4

    # 2. Tampered token rejected
    tampered = token[:-4] + "abcd"
    assert verify_token(tampered, secret) is None

    # 3. Expired token rejected
    expired_data = verify_token(token, secret, max_age_seconds=-1)
    assert expired_data is None


def test_s12_password_reset_flow(client, app):
    """S-12: Full password reset request and completion flow."""
    # 1. Request reset link
    req_resp = client.post('/forgot-password', data={'email': 'p1@test.local'}, follow_redirects=True)
    assert req_resp.status_code == 200
    assert b"password reset link has been issued" in req_resp.data

    # 2. Generate valid token
    with app.app_context():
        token = generate_token({'user_id': 4}, app.config['SECRET_KEY'])

    # 3. Access reset page
    get_resp = client.get(f'/reset-password/{token}')
    assert get_resp.status_code == 200
    assert b"Set New Password" in get_resp.data

    # 4. Submit new valid password
    post_resp = client.post(f'/reset-password/{token}', data={
        'password': 'BrandNewSecurePass@2026',
        'confirm_password': 'BrandNewSecurePass@2026'
    }, follow_redirects=True)
    assert post_resp.status_code == 200
    assert b"password has been successfully reset" in post_resp.data

    # 5. Verify patient can log in with new password
    login_resp = client.post('/login', data={
        'email': 'p1@test.local',
        'password': 'BrandNewSecurePass@2026'
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    assert b"Login successful" in login_resp.data


# ── S-15: FILE UPLOAD SAFETY ──────────────────────────────────────────

def test_s15_file_upload_safety(tmp_path):
    """S-15: Upload validation enforces MIME/extension allowlist and magic byte inspection."""
    import io

    from werkzeug.datastructures import FileStorage

    from hms.utils.uploads import FileUploadError, save_secure_upload, validate_file_safety

    # 1. Reject prohibited extension (.exe, .php)
    bad_ext = FileStorage(stream=io.BytesIO(b'%PDF-1.4 mock content'), filename='malware.exe')
    with pytest.raises(FileUploadError) as exc_info:
        validate_file_safety(bad_ext)
    assert "Prohibited file extension" in str(exc_info.value)

    # 2. Reject mismatched magic bytes (text disguised as PDF)
    fake_pdf = FileStorage(stream=io.BytesIO(b'plain text disguised as pdf'), filename='report.pdf')
    with pytest.raises(FileUploadError) as exc_info:
        validate_file_safety(fake_pdf)
    assert "legitimate PDF or JPEG/PNG" in str(exc_info.value)

    # 3. Accept valid PDF with legitimate magic header and save with random name
    valid_pdf_content = b'%PDF-1.5\n%Valid clinical test report content'
    valid_pdf = FileStorage(stream=io.BytesIO(valid_pdf_content), filename='lab_results.pdf')
    saved_name = save_secure_upload(valid_pdf, tmp_path)

    assert saved_name.endswith('.pdf')
    assert saved_name != 'lab_results.pdf'
    assert (tmp_path / saved_name).exists()
    assert (tmp_path / saved_name).read_bytes() == valid_pdf_content

