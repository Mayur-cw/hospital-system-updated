# REPOSITORY BASELINE AUDIT — HOSPITAL OS
**Audit Date:** 2026-11-17  
**Auditor / Agent:** Antigravity (Google DeepMind)  
**Repository Source:** `https://github.com/Mayur-cw/hospital-system-updated.git`  
**Git Branch:** `feature/hospital-os-champion` (branched from `main`)  
**Baseline Git Commit SHA:** `ec332d26d815434e817b1b49e66c83311f5dc79d`  
**Commit Date:** Sat May 9 13:32:37 2026 +0530  
**Commit Message:** `Final commit, our project has been completed`  
**Initial Repository Commit:** `3c03c37` (2026-04-29) | Total 36 historical commits  
**System Status Mode:** `DEV_ONLY` (Transitioning to `DEMO_READY`)

---

## 1. Executive Summary & Status Classification
The target repository is a student-built hospital management system developed using Flask, Flask-SQLAlchemy, and MySQL. It was structured as a DBMS mini-project. While it demonstrates basic CRUD flows (login, doctor/patient/admin dashboards, appointment booking, basic inpatient room allocation), it contains **critical safety, privacy, authorization, and financial integrity defects** that make it unsafe for clinical or commercial production.

This audit establishes the baseline facts through local code inspection, dependency verification, and route-level analysis. Findings are classified as **[VERIFIED]** (proven directly from checked-out source code), **[INFERRED]** (deduced from architecture/patterns), or **[BLOCKED]** (cannot be verified without external live integration).

---

## 2. File & Component Inventory

### Python Source Files
| File Path | Lines | Responsibilities | Verified Issues |
|---|---|---|---|
| `PROJECT/app.py` | 42 | Application bootstrap, blueprint registration, login manager setup | F-02: `FLASK_DEBUG` defaults to `'true'`. No app factory. |
| `PROJECT/config.py` | 11 | Configuration class | F-01: Hardcoded fallback `SECRET_KEY` and literal MySQL `root` URI with embedded password. |
| `PROJECT/models.py` | 113 | SQLAlchemy ORM models (`User`, `Appointments`, `MedicalRecord`, `Doctors`, `AuditLog`, `Billing`, `Room`, `Admission`, `Test`) | F-09: `CASCADE` deletions. F-14: Appointments store denormalized strings for `doctor`, `date`, `time`, `dept`. |
| `PROJECT/routes/__init__.py` | 0 | Package marker | Empty. |
| `PROJECT/routes/auth.py` | 103 | Authentication (login, signup, logout, profile) | F-11: Open redirect on `next`. F-12: State-changing GET logout. F-13: No CSRF. |
| `PROJECT/routes/main.py` | 111 | Index routing, doctor queue calculation, public doctor directory | F-23: Unbounded query / in-memory sorting of all records for simple status flags. |
| `PROJECT/routes/patient.py` | 267 | Patient booking, history, invoices, simulated payment, receipt | F-06: Simulated payment instantly marks invoice `Paid`. F-16: Booking unvalidated server-side. F-17: Any doctor can view any booking success. |
| `PROJECT/routes/doctor.py` | 193 | Doctor workflow (attend, miss, add record, admissions, discharge) | F-03: `mark_missed`/`mark_attended` lack provider ownership checks. F-04: `add_record` lacks encounter assignment checks. F-05: `discharge_patient` lacks ownership and idempotency. |
| `PROJECT/routes/admin.py` | 566 | Admin dashboard, staff/doctor/patient CRUD, appointments, rooms, discharge | F-07: Admin discharge does not generate bill; doctor discharge does. F-09: Permanent appointment hard delete. F-18: Open redirect via `redirect_url`. |

### Database Schemas & Seed Scripts
| File Path | Lines | Purpose | Verified Issues |
|---|---|---|---|
| `hms.sql` | 273 | MySQL DDL, triggers, views, and `BookAppointmentSafe` procedure | F-08: Destructive `DROP TABLE IF EXISTS`. F-09: `ON DELETE CASCADE`. F-15: Gap-lock concurrency hazard. |
| `seed_secure_accounts.sql` | 129 | Initial database accounts and demo records | F-10: Public default passwords (`mayur`, `siddhi`, `rehman`), personal mobile numbers, and unverified mock data. |
| `testing.sql` | 6 | Ad-hoc SQL insert commands | Scratch testing file; untracked schema migration risk. |

### Templates (24 files)
- Base layout: `PROJECT/templates/base.html` (heavy inline CSS, student branding footer)
- Home/Portals: `index.html`, `doctor_directory.html`
- Auth: `auth/login.html`, `auth/profile.html`, `auth/signup.html`
- Bookings/Billing: `bookings/appointment_history.html`, `bookings/book_appointment.html`, `bookings/booking_success.html`, `bookings/edit.html`, `bookings/my_bills.html`, `bookings/pay_invoice.html`, `bookings/receipt.html`
- Records: `records/add_record.html`, `records/doctor_admissions.html`, `records/edit_record.html`, `records/view_record.html`
- Admin: `admin/admin_appointments.html`, `admin/admin_dashboard.html`, `admin/admin_doctors.html`, `admin/admin_financials.html`, `admin/admin_patients.html`, `admin/admin_rooms.html`, `admin/admin_staff.html`, `admin/audit_logs.html`

### Static Assets
- `PROJECT/static/css/virtualregister.css`
- `PROJECT/static/images/bg1.jpg`
- `PROJECT/static/images/doc.jpg`

---

## 3. Dependency & Environment Analysis
Current `Commands/requirements.txt`:
```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
SQLAlchemy==1.4.52
Jinja2==3.1.4
MarkupSafe==2.1.5
Werkzeug==2.3.7
pytz==2024.1
mysqlclient==2.2.4
```

### Key Gaps
1. **No CSRF Protection Library**: Missing `Flask-WTF` or equivalent token validation.
2. **No Migration Tool**: Missing `alembic` or `Flask-Migrate`. Database evolution was done via raw `DROP TABLE` SQL scripts.
3. **No Test Framework**: Missing `pytest`, `pytest-cov`, or any test suites.
4. **No Environment Management**: Missing `python-dotenv` for loading safe environment variables.

---

## 4. Comprehensive Audit Findings (F-01 through F-25)

| ID | Priority | Description | Verified Code Reference | Status |
|---|---|---|---|---|
| **F-01** | P0 | Hardcoded fallback SECRET_KEY and root MySQL connection string with embedded password | `PROJECT/config.py:5,8` | **VERIFIED** |
| **F-02** | P0 | `FLASK_DEBUG` defaults to `'true'` in application bootstrap | `PROJECT/app.py:42` | **VERIFIED** |
| **F-03** | P0 | Doctor routes `mark_missed` and `mark_attended` do not verify doctor-appointment assignment | `PROJECT/routes/doctor.py:27-50` | **VERIFIED** |
| **F-04** | P0 | Doctor route `add_record` allows any doctor to add medical records to any appointment | `PROJECT/routes/doctor.py:51-103` | **VERIFIED** |
| **F-05** | P0 | Doctor route `discharge_patient` has no doctor-patient assignment check and no idempotency/duplicate check | `PROJECT/routes/doctor.py:118-146` | **VERIFIED** |
| **F-06** | P0 | Patient route `process_payment` sets invoice to `Paid` on browser form submission without gateway verification | `PROJECT/routes/patient.py:227-253` | **VERIFIED** |
| **F-07** | P0 | Admin discharge does not generate an invoice; doctor discharge does. Severe domain inconsistency | `PROJECT/routes/admin.py:543-566` vs `PROJECT/routes/doctor.py:118-146` | **VERIFIED** |
| **F-08** | P0 | `hms.sql` executes destructive `DROP TABLE IF EXISTS` on setup | `hms.sql:23-31` | **VERIFIED** |
| **F-09** | P0 | Cascading foreign key deletes (`ON DELETE CASCADE`) and admin hard deletion of appointments destroy clinical/financial history | `hms.sql:54,67,92-95,106,120-121`, `PROJECT/routes/admin.py:388-404` | **VERIFIED** |
| **F-10** | P0 | Public default passwords and real-looking personal numbers committed in seed data | `seed_secure_accounts.sql:25-70` | **VERIFIED** |
| **F-11** | P1 | Open redirect vulnerability in login route via unvalidated `next` parameter | `PROJECT/routes/auth.py:22-23` | **VERIFIED** |
| **F-12** | P1 | Logout route uses HTTP GET method, allowing state modification via link pre-fetching or CSRF | `PROJECT/routes/auth.py:57-62` | **VERIFIED** |
| **F-13** | P0 | Complete absence of CSRF protection across all session-authenticated POST forms | Entire app / templates | **VERIFIED** |
| **F-14** | P1 | Denormalized string storage for appointment doctor name, specialty, date, and time strings | `PROJECT/models.py:39-44`, `hms.sql:60-65` | **VERIFIED** |
| **F-15** | P1 | `BookAppointmentSafe` procedure uses `COUNT(*) ... FOR UPDATE` without a database unique constraint, risking race conditions | `hms.sql:259-266` | **VERIFIED** |
| **F-16** | P1 | Booking endpoint accepts arbitrary text parameters from client without schedule validation; returns last appointment by user ID | `PROJECT/routes/patient.py:50-93` | **VERIFIED** |
| **F-17** | P1 | Booking success screen allows ANY doctor to view any patient's booking confirmation | `PROJECT/routes/patient.py:109` | **VERIFIED** |
| **F-18** | P1 | Admin appointment update route accepts unvalidated `redirect_url` form field, causing open redirect | `PROJECT/routes/admin.py:376,386` | **VERIFIED** |
| **F-19** | P1 | Room charge billing uses Python floating-point arithmetic and `delta.days` without tariff rules | `PROJECT/routes/doctor.py:132-137` | **VERIFIED** |
| **F-20** | P1 | Raw system exceptions flashed directly to client UI | `PROJECT/routes/doctor.py:98` | **VERIFIED** |
| **F-21** | P1 | Massive inline CSS blocks and inconsistent styling across templates | `PROJECT/templates/base.html`, `index.html`, etc. | **VERIFIED** |
| **F-22** | P1 | Clinical prescription is a single unformatted textarea with no structured dosage, frequency, or safety checks | `PROJECT/templates/records/add_record.html:96-99` | **VERIFIED** |
| **F-23** | P1 | Doctor index route loads all medical records into memory (`MedicalRecord.query.all()`) to calculate status counts | `PROJECT/routes/main.py:33` | **VERIFIED** |
| **F-24** | P1 | Lack of `.gitignore`, tracked virtualenv, lack of automated test suite or CI configuration | Root repository tree | **VERIFIED** |
| **F-25** | P2 | Footer retains student DBMS project labels and lacks commercial branding/governance configuration | `PROJECT/templates/base.html` | **VERIFIED** |

---

## 5. Security & Risk Ranking (Triage)
1. **Critical (P0 - Immediate Stop-Ship)**: F-01 (Secrets), F-02 (Debug default), F-03 & F-04 & F-05 (BOLA/IDOR on clinical notes/status/discharge), F-06 (Fake payment marked paid), F-07 (Inconsistent billing postcondition), F-08 & F-09 (Destructive schema drops and cascade deletion), F-10 (Seed secrets), F-13 (CSRF missing).
2. **High (P1 - Required for Pilot)**: F-11 & F-18 (Open redirects), F-12 (GET logout), F-14 & F-15 (Denormalized appointment strings and race hazards), F-16 & F-17 (Broken appointment authorization), F-19 (Float money calculations), F-20 (Exception leakage), F-22 (Unstructured medication safety), F-23 (N+1 memory loading), F-24 (Repository hygiene & lack of tests).
3. **Medium (P2 - Experience & Compliance)**: F-21 (Design system inconsistency), F-25 (Academic project labeling).
