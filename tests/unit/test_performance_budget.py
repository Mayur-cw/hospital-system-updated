# tests/unit/test_performance_budget.py - Performance Budget & Query Counter (T-09)
from sqlalchemy import event

from hms.extensions import db


class QueryCounter:
    """Context manager to count executed SQL queries on a database engine (T-09)."""

    def __init__(self, engine):
        self.engine = engine
        self.count = 0
        self.queries = []

    def __enter__(self):
        self.count = 0
        self.queries.clear()
        event.listen(self.engine, "before_cursor_execute", self._callback)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        event.remove(self.engine, "before_cursor_execute", self._callback)

    def _callback(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1
        self.queries.append(statement)


def test_t09_admin_dashboard_query_budget(client, app):
    """T-09: Admin dashboard must execute <= 10 queries per request (budget gate)."""
    client.post("/login", data={"email": "admin@test.local", "password": "AdminPass@123"}, follow_redirects=True)

    with QueryCounter(db.engine) as qc:
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200

    print(f"\nAdmin Dashboard Query Count: {qc.count}")
    assert qc.count <= 10, f"Performance Budget Exceeded: Admin dashboard executed {qc.count} queries (budget <= 10)"


def test_t09_admin_listings_no_n_plus_one(client, app):
    """T-09: Admin listings must use eager loading / joinedload to prevent N+1 queries."""
    client.post("/login", data={"email": "admin@test.local", "password": "AdminPass@123"}, follow_redirects=True)

    # 1. Doctors directory
    with QueryCounter(db.engine) as qc_doc:
        resp_doc = client.get("/admin/doctors")
        assert resp_doc.status_code == 200
    assert qc_doc.count <= 10, f"Admin doctors list executed {qc_doc.count} queries"

    # 2. Appointments list
    with QueryCounter(db.engine) as qc_apt:
        resp_apt = client.get("/admin/appointments")
        assert resp_apt.status_code == 200
    assert qc_apt.count <= 10, f"Admin appointments list executed {qc_apt.count} queries"

    # 3. Rooms board
    with QueryCounter(db.engine) as qc_room:
        resp_room = client.get("/admin/rooms")
        assert resp_room.status_code == 200
    assert qc_room.count <= 10, f"Admin rooms list executed {qc_room.count} queries"


def test_t09_patient_and_doctor_dashboard_query_budget(client, app):
    """T-09: Clinical role dashboards must remain under performance budget."""
    # Patient dashboard
    client.post("/login", data={"email": "p1@test.local", "password": "PatientPass@123"}, follow_redirects=True)
    with QueryCounter(db.engine) as qc_patient:
        resp_patient = client.get("/dashboard")
        assert resp_patient.status_code == 200
    assert qc_patient.count <= 10, f"Patient dashboard executed {qc_patient.count} queries"

    # Doctor dashboard
    client.post("/logout", follow_redirects=True)
    client.post("/login", data={"email": "doc1@test.local", "password": "DoctorPass@123"}, follow_redirects=True)
    with QueryCounter(db.engine) as qc_doc:
        resp_doc = client.get("/dashboard")
        assert resp_doc.status_code == 200
    assert qc_doc.count <= 10, f"Doctor dashboard executed {qc_doc.count} queries"
