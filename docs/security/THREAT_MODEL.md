# THREAT MODEL & PRIVACY ARCHITECTURE — HOSPITAL OS
**Standard Reference:** OWASP ASVS 5.0.0 (Level 1/2 Controls) & STRIDE Methodology  
**Data Protection Framework:** India Digital Personal Data Protection (DPDP) Act 2023 & DPDP Rules 2025  
**Data Classification:** Protected Health Information (PHI) — Highly Sensitive Confidential

---

## 1. STRIDE Threat Analysis & Applied Mitigations

| Threat Category | Hazard Scenario | Target Asset | Architectural Mitigation | Automated Test Reference |
|---|---|---|---|---|
| **Spoofing** | Attacker logs in using default seed accounts or brute-forces passwords. | User Credentials & Session | Remove hardcoded passwords. Enforce strong PBKDF2 hashing, login rate-limiting, and account lockout after repeated failures. | `T-AUTH-001`, `SEED-001` |
| **Tampering** | Doctor silently edits past diagnosis without an audit trail, or user tampers with bill amount in HTTP POST. | Clinical Notes & Invoices | Signed clinical notes are immutable (`CLINICAL_NOTE_REVISION` append-only). Invoices are computed server-side from versioned tariff masters. | `T-NOTE-001`, `BILL-001` |
| **Repudiation** | Attacker claims they never accessed or altered a patient chart. | Legal Chain of Custody | Centralized `AuditLog` captures user ID, action, timestamp, IP address, and resource ID for every clinical and administrative event. | `AUDIT-001` |
| **Information Disclosure (BOLA / IDOR)** | Patient or doctor manipulates integer IDs in URLs (`/bills/4/invoice`, `/add_record/2`) to view or edit unassigned records. | Patient Records & Bills | Centralized Policy Engine enforces object-level care-team ownership on every query. Deny by default. | `T-AUTH-001` to `T-AUTH-005` |
| **Denial of Service** | Malicious actor spams concurrent appointment bookings to exhaust doctor slots or lock database tables. | Scheduling Availability | Transactional row-level locking with unique database constraint `(doctor_id, date, time)` and request rate-limiting. | `T-APPT-001` |
| **Elevation of Privilege** | Normal patient or doctor submits form to `/admin/add_staff` or `/admin/delete_room`. | Administrative Controls | `@require_roles('Admin')` decorator validated strictly against server-side session role. | `T-AUTH-002` |

---

## 2. Web Vulnerability Defenses

### 2.1 Cross-Site Request Forgery (CSRF)
- **Vulnerability Found (F-13):** Zero CSRF protection in original repository.
- **Remediation:** Integrated `Flask-WTF` `CSRFProtect(app)`. All state-mutating HTTP methods (`POST`, `PUT`, `DELETE`, `PATCH`) must supply a valid CSRF token.
- **GET Logout Fix (F-12):** Converted logout to `POST /logout` with CSRF validation.

### 2.2 Open URL Redirection
- **Vulnerability Found (F-11, F-18):** `routes/auth.py` and `routes/admin.py` blindly redirected to query param `next` and form field `redirect_url`.
- **Remediation:** Introduced `is_safe_url()` validator ensuring target redirects are strictly relative to the host application domain. External redirects are rejected.

### 2.3 Injection & SQL Portability
- **Defense:** Parameterized queries via SQLAlchemy ORM; eliminate raw unparameterized SQL concatenation.
- **DDL Safety:** Eradicate `DROP TABLE IF EXISTS` and `ON DELETE CASCADE` from application workflows to protect patient records.

---

## 3. India DPDP Act & Privacy Controls
1. **Notice & Purpose Specification**: Clear privacy notice on registration identifying the hospital as Data Fiduciary.
2. **Data Minimization**: Mandatory fields restricted to operational clinical requirements (Name, Phone, Age/DOB, Gender, Chief Complaint).
3. **No External PHI Leakage**:
   - Zero real patient data in development, demo seeds, or logs.
   - External notification channels (SMS/WhatsApp) must never transmit diagnostic details in plaintext notifications.
   - No unapproved third-party analytics or AI API calls passing PHI.
