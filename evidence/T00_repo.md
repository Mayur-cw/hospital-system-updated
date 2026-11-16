# EVIDENCE: PHASE T-00 GROUND TRUTH & REPOSITORY AUDIT
**Date:** 2026-11-17  
**Execution Environment:** macOS Darwin, Local Python 3.9.6 venv (`.venv`), MySQL & PostgreSQL services active locally.  
**Branch:** `feature/hospital-os-champion`  
**Base Commit:** `ec332d26d815434e817b1b49e66c83311f5dc79d` (Sat May 9 13:32:37 2026 +0530)

---

## 1. Git Repository Verification
- **Remote Origin URL:** `https://github.com/Mayur-cw/hospital-system-updated.git`
- **Initial Commit:** `3c03c37` (2026-04-29 11:53:47 +0530)
- **Total Commit Count:** 36 commits on `main`
- **Feature Branch Created:** `feature/hospital-os-champion`
- **Integrity Status:** Original `main` HEAD preserved. Working tree isolated.

---

## 2. File and Component Inventory
```
Total Tracked Files: 38
Python Modules: 8 (app.py, config.py, models.py, routes/{__init__,admin,auth,doctor,main,patient}.py)
SQL DDL & Seed Scripts: 3 (hms.sql, seed_secure_accounts.sql, testing.sql)
Jinja2 HTML Templates: 24 (base.html, index.html, doctor_directory.html, admin/*, auth/*, bookings/*, records/*)
Static Assets: 3 (virtualregister.css, bg1.jpg, doc.jpg)
Support Docs: 1 (Commands/one step command.txt)
Tracked Binaries: 0
```

---

## 3. Verified Safety Blockers (Release-Blocker Ledger)

| ID | Issue Description | Impact | Verified Location | Fix Phase |
|---|---|---|---|---|
| **BLK-01** | Exposed MySQL root URI with password & default SECRET_KEY | Critical credential exposure | `PROJECT/config.py:5,8` | T-01 |
| **BLK-02** | Default `FLASK_DEBUG=True` | Remote code execution / debug exposure | `PROJECT/app.py:42` | T-01 |
| **BLK-03** | Total lack of CSRF protection on POST routes | Client-side request forgery | Global / all forms | T-01 |
| **BLK-04** | Missing object-level authorization on clinical charts and appointments | BOLA/IDOR cross-doctor edits | `PROJECT/routes/doctor.py:27-146` | T-01 |
| **BLK-05** | Simulated payment automatically marks invoices `Paid` | False financial settlement | `PROJECT/routes/patient.py:227-253` | T-01 |
| **BLK-06** | Inconsistent discharge logic between Admin and Doctor | Unbilled discharges & duplicate bills | `admin.py:543` vs `doctor.py:118` | T-01 |
| **BLK-07** | Destructive `DROP TABLE` and `ON DELETE CASCADE` DDL | Irreversible clinical data loss | `hms.sql:23-31, 54-121` | T-02 |
| **BLK-08** | Committed default credentials and sample PII | Credential abuse | `seed_secure_accounts.sql` | T-01 |
| **BLK-09** | Open redirects on login `next` and admin appointment update | Phishing / navigation hijack | `routes/auth.py:22`, `routes/admin.py:376` | T-01 |
| **BLK-10** | Concurrency race condition on appointment booking | Overbooking clinical schedules | `hms.sql:259-266` | T-02 |
