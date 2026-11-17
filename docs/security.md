# Security Architecture & Operations Manual

**Hospital Management System — Hedgewar Hospital**  
**Document Revision:** 2.0 (Security Hardened Baseline)

---

## 1. Threat Model & Principles
Hedgewar Hospital manages protected health information (PHI), clinical diagnoses, prescription histories, and financial transactions. Our architecture strictly adheres to:
1. **Deny by Default:** All clinical and administrative endpoints reject unauthorized access by default with HTTP 403 Forbidden.
2. **Database-Enforced Integrity:** Critical invariants (such as appointment double-booking concurrency and active room exclusivity) are guaranteed by database schema constraints and transactions.
3. **Data Loss Prevention:** Clinical records and audit entries are immutable and never subject to hard cascades (`ON DELETE RESTRICT`). Records use soft deletion (`SoftDeleteMixin`).

---

## 2. Role-Based Access Control (RBAC) & Policies (S-05)

### Role Hierarchy
* **Admin:** System provisioning, department and room management, staff onboarding, financial audits, full audit trail access.
* **Doctor:** Clinical consultations, prescribing, writing diagnosis, approving inpatient admissions and recommending discharge for assigned patients.
* **Patient:** Managing personal appointment schedule, viewing own prescription records, settling hospital invoices online.
* **Receptionist / Billing Cashier:** Patient check-in, counter cash invoice settlement, slot scheduling.

### Object-Level Ownership Rules
* Doctors can only mutate appointments and write clinical charts for patients on their assigned schedule (`appointment.doctor_id == current_doctor.id`).
* Patients can only view and settle invoices assigned to their account (`invoice.patient_id == current_user.id`).
* Physical counter cash payments cannot be self-processed by patients online (B-18); only authorized billing cashiers can record cash transactions.

---

## 3. Database Least Privilege & Connection Security (S-11)

In production, database access is segregated across two separate MySQL database accounts:

| Role | MySQL User | Privileges | Purpose |
|---|---|---|---|
| **Application Runtime** | `hms_app` | `SELECT, INSERT, UPDATE` on `hms.*` | Serves web traffic. Cannot `DROP`, `ALTER`, or `TRUNCATE` tables. |
| **Migration Runner** | `hms_migrate` | `ALL PRIVILEGES` on `hms.*` | Executed only by CI/CD during `alembic upgrade head`. |

### Connection Hardening
* **Encoding:** `utf8mb4` with `utf8mb4_unicode_ci` collation.
* **TLS:** MySQL connections require TLS in production (`ssl_ca`, `ssl_verify_cert=True`).
* **Root Lockout:** Application startup aborts immediately if default `root` credentials or unsecured development connection strings are detected.

---

## 4. Sensitive Data Handling & PHI Protection (S-13)

* **Zero PHI in Logs:** Application logging sanitizes medical diagnoses and prescription payloads. Audit events record entity IDs, actions, and actors, avoiding sensitive text dumping in log aggregators.
* **Clinical Access Auditing:** Any clinical record read by authorized staff produces an audit event recording the viewing practitioner and timestamp.
* **Data Retention & Right to be Forgotten:** Patient deletion requests trigger soft deactivation (`is_active = False, deleted_at = UTC`). Medical records are preserved for statutory regulatory compliance (retention period) under restricted archive access.

---

## 5. File Upload Safety (S-15)

Clinical attachments and laboratory diagnostic reports are protected by:
* **MIME and Extension Allowlist:** Only `.pdf`, `.png`, and `.jpg` / `.jpeg` files are accepted.
* **Magic Byte Inspection:** File headers are validated against binary signatures (`%PDF`, PNG signature, JPEG SOI marker) to prevent disguised executable uploads.
* **Storage Isolation:** Files are stored in a dedicated `uploads/` volume strictly outside the web server root.
* **Filename Sanitization:** Uploads are assigned cryptographically random UUIDs (`uuid.uuid4().hex`) to neutralize directory traversal and script execution vectors.
* **Delivery:** Files are streamed through authorized endpoints checking object-level view permissions with `Content-Disposition: attachment`.

---

## 6. Password Policy & Cryptography (S-06, S-12)

* **Passphrase Length:** Minimum 10 characters.
* **Breach Protection:** Automatically rejects trivial and common breached passphrases.
* **Hashing Algorithm:** Uses Werkzeug's modern Scrypt password hashing with unique salt.
* **Account Recovery:** Password reset tokens use `itsdangerous.URLSafeTimedSerializer` signed with `SECRET_KEY`, expiring strictly in 30 minutes. Single-use and tamper-proof.
