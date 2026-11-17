# tests/unit/test_phase6_reliability.py - Tests for Phase 6 Reliability & Observability (R-01 to R-07)
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError, OperationalError

from hms.logging import JSONFormatter, scrub_phi
from hms.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    NotificationOutbox,
    User,
    db,
)
from hms.services.appointments import InvalidStateTransitionError

# ── R-01: STRUCTURED LOGGING & PHI SCRUBBING ──────────────────────────────

def test_r01_phi_scrubbing_dictionary_and_text():
    """R-01: Sensitive clinical/auth information must be redacted from log payloads."""
    sensitive_data = {
        "username": "dr.sharma",
        "password": "SuperSecretPassword123!",
        "token": "bearer-xyz-12345",
        "diagnosis": "Acute myocardial infarction",
        "symptoms": "Chest pain radiating to left arm",
        "prescription": "Aspirin 75mg daily",
        "allergies": "Penicillin",
        "email_in_text": "Contact patient at patient.doe@example.com immediately",
        "phone_in_text": "Emergency phone: 555-019-2834",
    }
    scrubbed = scrub_phi(sensitive_data)
    assert scrubbed["password"] == "[REDACTED]"
    assert scrubbed["token"] == "[REDACTED]"
    assert scrubbed["diagnosis"] == "[REDACTED]"
    assert scrubbed["symptoms"] == "[REDACTED]"
    assert scrubbed["prescription"] == "[REDACTED]"
    assert scrubbed["allergies"] == "[REDACTED]"
    assert "[EMAIL_REDACTED]" in scrubbed["email_in_text"]
    assert "patient.doe@example.com" not in scrubbed["email_in_text"]
    assert "[PHONE_REDACTED]" in scrubbed["phone_in_text"]
    assert "555-019-2834" not in scrubbed["phone_in_text"]
    assert scrubbed["username"] == "dr.sharma"


def test_r01_json_formatter_outputs_valid_json():
    """R-01: JSONFormatter produces valid structured JSON lines."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Clinical service executed successfully with password=Secret!",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert "timestamp" in parsed
    assert "password=[REDACTED]" in parsed["message"] or "Secret!" not in parsed["message"]


def test_r01_request_id_in_error_pages(client):
    """R-01: Error pages must prominently display the request/incident ID."""
    resp = client.get("/non-existent-route-for-404-check", headers={"X-Request-ID": "test-req-9999"})
    assert resp.status_code == 404
    assert resp.headers.get("X-Request-ID") == "test-req-9999"
    assert b"test-req-9999" in resp.data


# ── R-02: HEALTH & READINESS PROBES ───────────────────────────────────────

def test_r02_healthz_endpoint(client):
    """R-02: /healthz returns 200 OK with process status."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "hedgewar-hms"
    assert "timestamp" in data


def test_r02_readyz_endpoint(client):
    """R-02: /readyz returns readiness state of database."""
    resp = client.get("/readyz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "migrations" in data


# ── R-03: GLOBAL ERROR HANDLING & CONFLICTS ───────────────────────────────

def test_r03_conflict_error_returns_409(client, app):
    """R-03: InvalidStateTransitionError is mapped to HTTP 409 Conflict."""
    @app.route("/test-trigger-conflict")
    def trigger_conflict():
        raise InvalidStateTransitionError("Cannot transition from Cancelled to Completed.")

    resp = client.get("/test-trigger-conflict", headers={"Accept": "application/json"})
    assert resp.status_code == 409
    data = resp.get_json()
    assert data["error"] == "Conflict"
    assert "Cannot transition from Cancelled to Completed" in data["description"]


def test_r03_integrity_error_returns_409(client, app):
    """R-03: Database IntegrityError is caught, rolled back, and returned as 409."""
    @app.route("/test-trigger-integrity")
    def trigger_integrity():
        raise IntegrityError("INSERT INTO appointments", {}, Exception("Duplicate entry"))

    resp = client.get("/test-trigger-integrity", headers={"Accept": "application/json"})
    assert resp.status_code == 409
    data = resp.get_json()
    assert data["error"] == "Conflict"


def test_r03_operational_error_returns_503(client, app):
    """R-03: Database OperationalError (e.g. timeout) returns 503 Service Unavailable."""
    @app.route("/test-trigger-operational")
    def trigger_operational():
        raise OperationalError("SELECT 1", {}, Exception("Lock wait timeout exceeded"))

    resp = client.get("/test-trigger-operational", headers={"Accept": "application/json"})
    assert resp.status_code == 503
    data = resp.get_json()
    assert data["error"] == "Service Unavailable"


# ── R-04: SCHEDULED JOBS (MARK-MISSED & SEND-REMINDERS) ───────────────────

def test_r04_mark_missed_command(app):
    """R-04: flask mark-missed transitions past due Scheduled appointments to Missed."""
    with app.app_context():
        doc = Doctor.query.first()
        patient = User.query.filter_by(usertype="Patient").first()

        # Create an appointment in the past (2 hours ago)
        past_time = datetime.now() - timedelta(hours=2)
        past_apt = Appointment(
            patient_id=patient.id,
            doctor_id=doc.id,
            department_id=doc.department_id,
            starts_at=past_time,
            duration_min=30,
            status=AppointmentStatus.SCHEDULED,
            reason="Routine past checkup",
        )
        db.session.add(past_apt)
        db.session.commit()
        apt_id = past_apt.id

        runner = app.test_cli_runner()
        result = runner.invoke(args=["mark-missed", "--grace-minutes", "30"])
        assert result.exit_code == 0
        assert "Processed" in result.output
        assert "missed appointments" in result.output

        # Verify state in DB
        db.session.expire_all()
        updated = db.session.get(Appointment, apt_id)
        assert updated.status == AppointmentStatus.MISSED

        # Test idempotency: running a second time should process 0
        result2 = runner.invoke(args=["mark-missed", "--grace-minutes", "30"])
        assert result2.exit_code == 0
        assert "Processed 0 missed appointments" in result2.output


def test_r04_send_reminders_idempotency(app):
    """R-04: flask send-reminders dispatches reminders and is idempotent."""
    with app.app_context():
        doc = Doctor.query.first()
        patient = User.query.filter_by(usertype="Patient").first()

        # Create an appointment tomorrow (24 hours ahead)
        future_time = datetime.now() + timedelta(hours=24)
        apt = Appointment(
            patient_id=patient.id,
            doctor_id=doc.id,
            department_id=doc.department_id,
            starts_at=future_time,
            duration_min=30,
            status=AppointmentStatus.SCHEDULED,
            reason="Upcoming checkup",
        )
        db.session.add(apt)
        db.session.commit()

        runner = app.test_cli_runner()
        res1 = runner.invoke(args=["send-reminders", "--lead-hours", "24", "--window-minutes", "60"])
        assert res1.exit_code == 0
        assert "1 dispatched" in res1.output

        # Verify an outbox record was created
        outbox = NotificationOutbox.query.filter_by(event_type="appointment_reminder").first()
        assert outbox is not None
        assert str(apt.id) in outbox.body

        # Re-run: Must be skipped due to idempotency guard
        res2 = runner.invoke(args=["send-reminders", "--lead-hours", "24", "--window-minutes", "60"])
        assert res2.exit_code == 0
        assert "0 dispatched, 1 skipped" in res2.output


# ── R-06: PRODUCTION SERVING & CACHE CONTROLS ─────────────────────────────

def test_r06_cache_control_headers(client):
    """R-06: Static assets have immutable long cache; sensitive routes have no-store."""
    # 1. Static asset long cache
    static_resp = client.get("/static/css/tokens.css")
    assert static_resp.status_code == 200
    assert "max-age=31536000" in static_resp.headers.get("Cache-Control", "")
    assert "public" in static_resp.headers.get("Cache-Control", "")

    # 2. Sensitive clinical route no-store
    bills_resp = client.get("/bills")
    # Redirects to login, but cache header must still be no-store
    assert "no-store" in bills_resp.headers.get("Cache-Control", "")


# ── R-07: SENTRY PHI SCRUBBER HOOK ────────────────────────────────────────

def test_r07_sentry_event_scrubbing():
    """R-07: Sentry before_send hook strips PII from crash reports."""
    raw_sentry_event = {
        "event_id": "99b0c7918a544c0183b0f5926c483a99",
        "level": "error",
        "message": "User failed to update diagnosis",
        "user": {
            "id": 12,
            "email": "private.patient@hedgewar.local",
            "phone": "555-010-9999",
        },
        "extra": {
            "prescription": "Morphine 10mg IV",
            "blood_group": "O+",
            "request_id": "req-xyz-777",
        }
    }
    scrubbed = scrub_phi(raw_sentry_event)
    assert scrubbed["extra"]["prescription"] == "[REDACTED]"
    assert scrubbed["extra"]["blood_group"] == "O+"
    assert scrubbed["extra"]["request_id"] == "req-xyz-777"
    assert "[EMAIL_REDACTED]" in scrubbed["user"]["email"]
    assert "[PHONE_REDACTED]" in scrubbed["user"]["phone"]
