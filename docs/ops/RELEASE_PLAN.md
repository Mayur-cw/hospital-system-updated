# OPERATIONS, BACKUP & RELEASE PLAN — HOSPITAL OS
**Deployment Targets:**
1. Managed Cloud (Indian Region — e.g. AWS ap-south-1 Mumbai / GCP asia-south1 Mumbai)
2. Hospital-Controlled On-Premises Appliance (Linux VM with local network isolation)

---

## 1. Environments & Deployment Separation
- **`development`**: Local developer machines, SQLite or local MySQL database, synthetic seed data only, `DEMO_ONLY=true`.
- **`staging`**: Mirror of production topology, anonymized or synthetic test patients, automated smoke test validation.
- **`production`**: Client-owned infrastructure, strict fail-closed configuration (missing `SECRET_KEY` or `DATABASE_URL` halts boot), `FLASK_DEBUG=false`, real patient data with full DPDP protections.

---

## 2. Backup & Restore Strategy
- **Daily Automated Encrypted Snapshot**: Database dumps encrypted with AES-256 before transport.
- **Recovery Point Objective (RPO)**: <= 1 hour (via WAL / transaction log archiving).
- **Recovery Time Objective (RTO)**: <= 2 hours (via automated script-driven restore).
- **Verified Restore Drill**: Script `scripts/restore_drill.sh` validates restore into an isolated staging schema and compares checksums and row counts.

---

## 3. Go-Live Release Gates & Verification

| Gate | Requirement | Evidence Required | Status |
|---|---|---|---|
| **Gate 1: Security & Auth** | All P0 ASVS controls met; no default credentials; CSRF on all POST; safe redirects; zero BOLA/IDOR. | Automated test suite `tests/test_authorization.py` passing 100%. | **READY** |
| **Gate 2: Data Invariants** | Concurrency test proves no double bookings; bed occupancy unique; no cascade drops. | Concurrency tests `tests/test_concurrency.py` passing. | **READY** |
| **Gate 3: Financial Integrity** | No false payment marking; unified idempotent discharge; Decimal money calculations. | Billing regression tests `tests/test_billing.py` passing. | **READY** |
| **Gate 4: Clinical Safety** | Signed notes immutable; structured prescriptions; visible allergy/risk indicators. | EMR workflow tests `tests/test_clinical.py` passing. | **READY** |
| **Gate 5: Operational UX** | Golden screens verified across desktop, tablet, and mobile with realistic synthetic data. | Browser test captures and visual design critique. | **READY** |
| **Gate 6: Compliance & Legal** | Third-party security assessment, clinical UAT signoff, DPDP notice and data processing agreements. | External hospital validation artifacts. | **BLOCKED (Requires External Stakeholder Signoff)** |
