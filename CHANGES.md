# CHANGES.md — HMS upgrade plan (single source of truth)

**Repo:** `Mayur-cw/hospital-system-updated` · **Audited commit:** `ec332d2` ("Final commit, our project has been completed") · **Audit date:** 2026-11-17
**Stack today:** Flask 2.3.3 · Flask-SQLAlchemy 3.0.5 / SQLAlchemy 1.4 · Flask-Login · MySQL (mysqlclient) · Jinja2 · Bootstrap 5.3.0 via CDN · Python 3.9
**Size today:** ~1.4k lines of Python, 25 templates / 6,809 template lines, 1 DDL file with 7 triggers + 2 views + 1 stored procedure, 0 tests, 0 CI, 0 Docker, no README.

---

## 0. How to read this file

| Marker | Meaning |
|---|---|
| ✅ **verified** | Confirmed by reading the code/SQL at commit `ec332d2`. File and line are given. |
| 🔎 **verify first** | Strongly suspected but depends on runtime/driver behavior. Reproduce it before changing anything. |
| **P0** | Feature is broken or there is a security/data-loss hole. Fix first. |
| **P1** | Required for "industry-grade". |
| **P2** | Important quality. |
| **P3** | Polish / stretch. |

Every item has an ID. Tick the checkbox only when the **Done when** condition is demonstrably true (test, screenshot, or command output). IDs are referenced from commits and phase notes (`fix(B-04): …`).

---

## 1. Decisions and why (read before coding)

These are the forks in the road. Each lists the options considered so the owner can learn the trade-off, not just the outcome.

| # | Decision | Chosen | Alternatives considered | Why |
|---|---|---|---|---|
| D1 | Rewrite vs refactor | **Refactor in place** | Rewrite as React/Next + FastAPI | The business rules (booking, admission, billing) already exist and mostly work. A rewrite throws them away, takes far longer, and is much harder for one person to understand and defend. Refactor with tests keeps value and teaches architecture. |
| D2 | Front-end approach | **Server-rendered Jinja + self-hosted Bootstrap 5 + a real design-system layer + small vanilla-JS modules** | Tailwind (needs Node build), SPA, HTMX-everything | No build toolchain to maintain; Bootstrap is already in use; a token + component layer fixes the real problem (inconsistency), not the framework. Small `data-*` driven JS modules make a strict CSP possible. |
| D3 | Brand | **Keep navy/teal + Syne/DM Sans**, drop Inter and Itim | Full re-brand | The tokens already exist in `base.html`. The problem is that 4 pages define a second, incompatible token set instead of using them, not that the palette is wrong. Consistency beats novelty. |
| D4 | Slot double-booking | **UNIQUE index on a generated "active slot" column** (see snippet in D-03) | Keep `BookAppointmentSafe` procedure; app-level locks; `SELECT … FOR UPDATE` on the doctor row | A schema constraint is enforced for every writer, is testable from Python, and cannot be bypassed. The procedure's `COUNT(*) … FOR UPDATE` check-then-insert is not a dependable uniqueness guarantee. |
| D5 | Audit trail | **App-written, append-only `audit_event` table** with actor, entity, before/after JSON, IP | Keep MySQL triggers | Triggers cannot know *who* (the web user), cannot log logins or record views, and the current ones mislabel events (B-16). Keep triggers only if they add value after the redesign. |
| D6 | Layering | **routes → services → models** (no repository layer) | Full repository/DDD | Services give testable business logic and one place for transactions. A repository layer is over-engineering at this size. |
| D7 | Schema changes | **Flask-Migrate (Alembic)**; `hms.sql` becomes a generated reference, not the source | Hand-run `.sql` scripts | `hms.sql` currently starts with `DROP TABLE IF EXISTS …` for every table, which is dangerous outside a classroom. |
| D8 | Payments | **`PaymentGateway` interface; `MockGateway` default; Razorpay test-mode adapter behind an env flag** | Hard-wire one provider; keep the fake | Real money flows need verification, idempotency and webhooks (F-06). The interface lets the project demo end-to-end without real credentials. |
| D9 | Background work | **APScheduler (or a `flask` CLI command run by cron)** for reminders and auto-"Missed" | Celery + Redis | Two periodic jobs do not justify a broker. Revisit if volume grows. |
| D10 | PDFs | **Print-optimized CSS first (U-12)**, WeasyPrint for server-side PDF as P3 | Headless Chrome | Print CSS is free and covers invoices/receipts/prescriptions. |
| D11 | Compliance language | **Build with data-protection principles; make no compliance claims** in UI or docs | Claim HIPAA/DPDP "compliant" | Certification is an organizational process, not a code property. Overclaiming is a liability. |

---

## 2. Executive summary of what the audit found

**Broken today (verified):** 4 "create doctor/admin" forms 404 · navbar search 404 · admin breadcrumbs/links 404 · admin invoice page 500 (missing template) · patients are linked to admin-only invoice/receipt routes · appointment "edit" page has no route · two discharge flows with different billing behavior (one bills, one does not; neither is idempotent).

**Security gaps (verified):** no CSRF on any of 34 POST forms + 2 `fetch` POSTs · DB root credentials and a fallback `SECRET_KEY` in source · public seed file documents the admin password · `debug` defaults to **true** · open redirects · no rate limiting · password change without current password · logout via GET · any doctor can mutate any appointment · patients can self-mark invoices "Paid" · every medical record loaded into memory on every history page.

**Data model debt (verified):** `date`/`time` stored as strings and sorted lexicographically · doctors referenced by *username string* (renaming a doctor orphans their schedule) · `slot` column overloaded as status · money as `float` · CASCADE deletes destroy clinical and financial records · ORM and DDL disagree on column types.

**UI/UX debt (verified):** besides `base.html`, 4 pages (`profile`, `doctor_directory`, `booking_success`, `book_appointment`) define their own `:root` with a second token set (`--primary`, `--header-start/-end`, `--border`) that does not match base's `--hms-*` · 4 font families · 22 page-level `<style>` blocks across 19 of 24 pages (`index.html`: 4 blocks + 90 inline `style=`) · 55 inline `onclick`, 28 on non-interactive elements (not keyboard accessible) · 8 `confirm()` + 3 `alert()` · hard-coded hrefs (the cause of several 404s) · no pagination anywhere · search hidden below `lg`.

**Repo hygiene (verified):** two committed virtualenvs (23 MB + 9.6 MB; 2,433 of 2,479 tracked files) · `.DS_Store` files · no `.gitignore`, README, tests, CI, Docker, `.env.example`.

---

## PHASE 0 — Repo hygiene and safety net

- [x] **H-01 · P0 · ✅ Remove committed virtualenvs and OS junk**
  - **Where:** `venv/` (23 MB), `PROJECT/venv/` (9.6 MB, contains macOS `.so` builds), `.DS_Store` ×3 (root, `PROJECT/`, `PROJECT/static/`), `.vscode/`.
  - **Change:** `git rm -r --cached` them; add a real `.gitignore` (Python, venv, `.env`, `.DS_Store`, IDE, `instance/`, `uploads/`, coverage, `node_modules`).
  - **Done when:** `git ls-files | wc -l` is under ~80 and a fresh clone has no `venv/`.
  - **Note:** history still contains them. Rewriting history (`git filter-repo`) is optional and **requires the owner's explicit approval**.
- [x] **H-02 · P0 · ✅ Remove hard-coded secrets**
  - **Where:** `PROJECT/config.py:5` (fallback `SECRET_KEY='hmsprojects_dev_key'`), `:8` (DB URI with `root` and a password).
  - **Change:** read everything from env; `Config` classes (Dev/Test/Prod); Prod **refuses to start** without `SECRET_KEY` and `DATABASE_URL`; add `.env.example` (no real values).
  - **Done when:** `grep -rnE "mysql://[^ ]*:[^ ]*@" --include=*.py .` finds nothing and Prod boot without env vars fails with a clear message.
  - **Owner action (not code):** the old DB password is in public git history. Change it on any machine/DB that ever used it.
- [x] **H-03 · P0 · ✅ Remove default credentials from the repo**
  - **Where:** `seed_secure_accounts.sql` header documents that admin/sample accounts use password `mayur`, doctor `siddhi`, patient `rehman`, and includes the hash recipe.
  - **Change:** delete credential hints. Provide `flask create-admin` (prompts for email + password, no echo) and `flask seed-demo` (dev only, refuses to run when `FLASK_ENV=production`, generates random passwords and prints them once).
  - **Done when:** no plaintext/guessable credential appears in any tracked file.
- [x] **H-04 · P1 · Python and dependency baseline**
  - **Where:** `Commands/requirements.txt` (Flask 2.3.3, Werkzeug 2.3.7, Jinja2 3.1.4, SQLAlchemy 1.4.52; venv is Python 3.9.6 — Python 3.9 reached end of life in Oct 2025).
  - **Change:** Python 3.12; Flask 3.x, Werkzeug 3.x, SQLAlchemy 2.x (2.0-style queries), Flask-SQLAlchemy 3.1; move to root `requirements.txt` (+ `requirements-dev.txt`) or `pyproject.toml`; run `pip-audit`; add Dependabot.
  - **Done when:** `pip-audit` reports no known vulnerabilities and the app boots on 3.12.
- [x] **H-05 · P2 · ✅ Delete dead code**
  - **Where:** `testing.sql` (contains `use hms;use hms;INSERT…`), `Test` model + `test` table (`models.py:11-15`, `hms.sql`), `PROJECT/static/css/virtualregister.css` (not referenced by any template; imports the Itim font; different palette), `Commands/one step command.txt` (superseded by README/Makefile).
- [x] **H-06 · P1 · Characterization tests before refactoring**
  - **Change:** pytest smoke tests that pin *current* behavior of: signup/login, booking, doctor check-in, record creation → invoice, payment, admission/discharge, admin CRUD. They will fail on the bugs in Phase 1; mark those `xfail(strict=True)` with the bug ID so fixing a bug flips it to a pass.
  - **Why:** refactoring without a safety net is how working features silently break.
- [x] **H-07 · P2 · README, LICENSE, CONTRIBUTING, `docs/` skeleton** (full content in Phase 8).

---

## PHASE 1 — Fix what is broken today (all independent, do in any order)

- [x] **B-01 · P0 · ✅ "Create doctor / admin" forms 404**
  - **Where:** `base.html:263`, `base.html:303`, `admin/admin_doctors.html:255`, `admin/admin_staff.html:258` all post to `/add_staff`. The blueprint is registered with `url_prefix='/admin'` (`app.py:39`), so the real URL is `/admin/add_staff`.
  - **Change:** `action="{{ url_for('admin.add_staff') }}"`.
  - **Done when:** creating a doctor from the navbar creates `user` + `doctors` rows (test).
- [x] **B-02 · P0 · ✅ Navbar search posts to a route that does not exist**
  - **Where:** `base.html:194` → `POST /search`; no such route. Also `d-none d-lg-block` hides it on mobile.
  - **Change:** implement F-02, visible on all breakpoints.
- [x] **B-03 · P0 · ✅ Dead dashboard links**
  - **Where:** `/admin` in `admin_patients.html:15`, `admin_doctors.html:15`; `/admin_dashboard` in `admin_staff.html:15`, `admin_appointments.html:90`, `index.html:461`. Real URL is `/admin/dashboard`.
  - **Change:** `url_for('admin.admin_dashboard')`. Add a test that crawls every `href`/`action` in rendered pages and asserts no 404 (see T-08).
- [x] **B-04 · P0 · ✅ Invoice pages: missing template and wrong-role links**
  - **Where:** `admin.py:434` renders `admin/admin_view_invoice.html`, which does not exist → 500. `bookings/appointment_history.html:322` and `:326` (shown to patients and doctors) link to `admin.view_receipt` / `admin.view_invoice`, which are admin-only → patients get "Unauthorized".
  - **Change:** one `billing.invoice_detail` / `billing.receipt` endpoint per role-appropriate policy (owner patient, admin/billing staff), one template; templates use a `bill_url(bill)` helper.
  - **Done when:** patient, admin each open their allowed invoice and receipt; others get 403 (authorization matrix test T-04).
- [x] **B-05 · P1 · ✅ Appointment edit has no route**
  - **Where:** `bookings/edit.html:30` posts to `/edit/{{ posts.apt_id }}`; no such route exists and no route renders the template. It is dead code that hints at a missing feature.
  - **Change:** implement reschedule (F-01) and delete the orphan template once replaced.
- [x] **B-06 · P0 · ✅ Two inconsistent discharge flows**
  - **Where:** `doctor.py:118-146` (bills; no check that this doctor owns the admission; no guard against discharging twice → duplicate invoice on double-click) vs `admin.py:543-566` (marks discharged but **never creates an invoice**).
  - **Change:** one `AdmissionService.discharge(admission_id, actor)`: row-lock the admission (`SELECT … FOR UPDATE`), reject if already discharged, verify actor permission, compute charges once, create one invoice (D-04), write an audit event, free the room. Both UIs call it. Disable the submit button on first click (U-10).
  - **Done when:** concurrent double-submit produces exactly one invoice (test T-03).
- [x] **B-07 · P1 · ✅ Room-day billing under-charges**
  - **Where:** `doctor.py:132-137` uses `delta.days` (floors) with a minimum of 1: a 47-hour stay bills 1 day. Consultation fee `500.00` is hard-coded at `doctor.py:89` and `:137`; amounts are cast through `float`.
  - **Change:** `Decimal` arithmetic; rule = number of started 24-hour blocks, minimum 1 (**confirm this business rule with the owner** and document it in `docs/billing.md`); fee comes from the doctor/department (D-06), not a constant.
- [x] **B-08 · P1 · ✅ Date comparison inconsistency**
  - **Where:** `models.py:41-42` declares `time`/`date` as `String(50)` but `hms.sql` defines `date DATE`. `patient.py:160` compares `apt.date == today` (a `date`) while `main.py:88` compares `apt.date == str(today)`; one of them can never be true depending on what the driver returns. 🔎 Reproduce which branch is wrong, then remove the whole class of bug via D-01.
- [x] **B-09 · P1 · ✅ Appointments sorted by time *string***
  - **Where:** `admin.py:327` `order_by(Appointments.time.asc())` on values like `'01:00 PM'`, `'09:00 AM'` — sorts "01:00 PM" before "09:00 AM". Same pattern in Python sorts using `strptime` over the whole table (`main.py:24`, `patient.py:128`).
  - **Change:** resolved by D-01 (`starts_at DATETIME`).
- [x] **B-10 · P1 · ✅ `get_booked_slots` crashes on bad input**
  - **Where:** `patient.py:25-28` — `request.get_json()` returns `None` for a non-JSON body → `AttributeError` → 500. No validation of date format or doctor.
  - **Change:** validate (F-03 replaces it with a typed `GET /api/doctors/<id>/slots?date=`), return 400 on bad input.
- [x] **B-11 · P1 · ✅ Booking swallows real errors and can redirect to the wrong appointment**
  - **Where:** `patient.py:95-98` catches every `Exception` and tells the user "slot just taken"; `patient.py:92` fetches "this user's latest appointment" after the procedure call instead of using the inserted id.
  - **Change:** `AppointmentService.book()` returns the created entity; only an `IntegrityError` on the unique slot index becomes "slot taken"; everything else is logged and shown as a generic error with a request id.
- [x] **B-12 · P1 · ✅ `add_record` crash and detail leak**
  - **Where:** `doctor.py:77-79` — `Doctors…first()` can be `None` → `doctor_profile.did` raises. `doctor.py:98` flashes `str(e)` (internal DB error text) to the user. No check that the appointment belongs to this doctor (`doctor.py:51-58`).
  - **Change:** ownership policy check (S-05), friendly error + log, no internals in the UI.
- [x] **B-13 · P0 · ✅ Room allocation race**
  - **Where:** `doctor.py:74-80` checks `room.status == 'Available'` then inserts an admission; status flips to `Occupied` only via the `admission_insert` trigger afterward. Two doctors can admit into the same room simultaneously.
  - **Change:** lock the room row (`with_for_update()`) inside the service transaction and set status explicitly; add a UNIQUE guard such that one active admission per room is enforced by the schema (generated-column trick as in D-03).
- [x] **B-14 · P0 · ✅ Renaming a doctor orphans their appointments**
  - **Where:** `Appointments.doctor` stores the *username* (`models.py:44`); ownership checks compare names (`doctor.py:18`, `:157`, `:181`). A doctor can rename themselves (`auth.py:84-86`) and an admin can too (`admin.py:207-208`); afterwards existing appointments no longer match.
  - **Change:** `doctor_id` foreign key (D-01) + data migration (see D-01 notes).
- [x] **B-15 · P1 · ✅ Admin create/edit validation holes**
  - **Where:** `admin.py:86` takes `usertype` from the form unvalidated (any string accepted); `admin.py:118-121`, `:205-208` change email with no uniqueness check → `IntegrityError` 500; `admin.py:89-95` has no server-side password or empty-field check (only HTML `minlength=6`).
  - **Change:** form classes with enum whitelists, uniqueness validators, password policy (S-06).
- [x] **B-16 · P1 · ✅ Room forms crash or hit DB errors**
  - **Where:** `admin.py:480-482`, `:509-513` call `.strip()` directly on `request.form.get(...)` (crashes on a missing field); `ward_type` is free text but the DDL column is `ENUM('General','ICU','VIP','Maternity')` (`hms.sql`); `rate_per_day` converted with `float()` and not range-checked.
- [x] **B-17 · P1 · ✅ No state-transition rules**
  - **Where:** `doctor.py:11-49` — a patient can cancel a Completed/Attended appointment; `mark_missed` and `mark_attended` check only that the user is *a* doctor, not the appointment's doctor (`doctor.py:27-49`).
  - **Change:** appointment state machine (F-04) enforced in `AppointmentService`; policies enforce ownership.
- [x] **B-18 · P0 · ✅ Patient can mark their own invoice "Paid"**
  - **Where:** `patient.py:227-252` — any POST with `payment_mode=cash` sets `status='Paid'`; `bank_name` is trusted free text; no payment record, no idempotency, no verification.
  - **Change:** F-06 (gateway abstraction, `Payment` table, cash recorded only by staff, webhook verification).
- [x] **B-19 · P0 · ✅ Hard deletes destroy medical and financial records**
  - **Where:** `admin.py:388-404` (delete appointment), `:163-167` (delete admin user), `:249-257` (delete doctor user) combined with `ON DELETE CASCADE` on `medical_records`, `billing`, `admissions` (`hms.sql`) and `cascade="all, delete-orphan"` (`models.py:29,32`).
  - **Change:** soft delete / deactivate (D-05); `RESTRICT` on clinical and financial FKs; destructive admin actions require typed confirmation and are audited.
- [x] **B-20 · P1 · ✅ Whole-table loads and N+1 queries**
  - **Where:** `MedicalRecord.query.all()` on every dashboard/history request (`patient.py:129`, `:154`, `:174`; `main.py:33`) loads **every patient's diagnosis and prescription** into memory just to collect ids. `admin.py:279` (count per patient) and `admin.py:331` (`User.query.get` per appointment) are N+1. No pagination anywhere.
  - **Change:** `EXISTS`/join queries, eager loading (`selectinload`), server-side pagination (F-12).
- [x] **B-21 · P2 · ✅ Audit trail is partly wrong**
  - **Where:** `hms.sql` — `appointment_delete` logs `'APPOINTMENT CANCELLED'` for hard deletes, while actual cancellation is an UPDATE logged only as `'APPOINTMENT UPDATED'` with no before/after; `audit_log.apt_id` is `NOT NULL`, so logins/user changes cannot be logged; `models.py:70` types `timestamp` as `String(50)` but DDL is `DATETIME`.
  - **Change:** D-09.
- [x] **B-22 · P2 · ✅ Profile: password and email change without re-authentication**
  - **Where:** `auth.py:76-92`. Anyone with a hijacked session can change email + password without knowing the current password; `.strip()` silently alters passwords (`auth.py:16`, `:38`, `:70`).
  - **Change:** S-06/S-12.
- [x] **B-23 · P2 · ✅ Phone column too short**
  - **Where:** `models.py:25` / `hms.sql` `VARCHAR(12)` — `+91 98500 64866` does not fit. Widen to 20 and validate (D-07).
- [x] **B-24 · P2 · 🔎 Toast close button**
  - **Where:** `base.html` toast markup uses `data-bs-dismiss="alert"` on an element without the Bootstrap `.alert` class. Confirm the ✕ works; if not, use the new toast component (U-04).
- [x] **B-25 · P3 · ✅ Invisible footer text and placeholder links**
  - **Where:** `base.html` footer — copyright uses `opacity-10` (effectively unreadable) and social links are `href="#"`. Footer brands the app as "DBMS Mini-Project". Replace with a real, accessible footer (U-05).

---

## PHASE 2 — Security hardening

- [x] **S-01 · P0 · CSRF protection everywhere** — Flask-WTF `CSRFProtect`; a `csrf_field()` macro in every one of the 34 POST forms; `X-CSRFToken` header on every `fetch` POST (2 today, `book_appointment.html:598`, `edit.html:184`). **Done when:** a POST without a token returns 400 for every mutating route (parametrized test).
- [x] **S-02 · P1 · Logout via POST** — `auth.py:57` is a GET (`href="/logout"` in `base.html`), so any page can log a user out. Use a small POST form.
- [x] **S-03 · P1 · Open redirects** — `auth.py:22-23` (`next`), `admin.py:376,396` (`redirect_url` hidden field), and several `request.referrer` redirects. Add `safe_redirect(target, fallback)` that accepts only same-host relative paths.
- [x] **S-04 · P1 · Rate limiting + lockout** — Flask-Limiter on login, signup, password reset, payment, search (e.g. login 5/min/IP+email; exponential backoff after repeated failures). Redis in production, in-memory in dev.
- [x] **S-05 · P0 · Central authorization (RBAC + object policies)**
  - **Where:** 52 copy-pasted `usertype ==/!=` checks across routes (admin 30, doctor 10, patient 8, main 3, auth 1).
  - **Change:** `Role` enum; `@roles_required(...)`; policy functions (`can_view_appointment(user, apt)`, `can_edit_record`, `can_view_invoice`, `can_discharge`) used by services; deny by default. Doctor ownership by `doctor_id`, never by name.
  - **Done when:** authorization matrix test (T-04) covers every route × role × owner/non-owner and passes.
- [x] **S-06 · P1 · Password policy** — minimum 10 characters, no composition rules, reject common/breached passwords (local list), never `.strip()` or truncate, show a strength hint; Werkzeug's current default hash (scrypt) for new hashes; rehash on login if the stored hash is the old pbkdf2 parameters.
- [x] **S-07 · P1 · Session and cookie settings** — `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE='Lax'`, `SESSION_COOKIE_SECURE` in prod, idle timeout (staff 30 min, patients 2 h), `session_protection='strong'`, opt-in "remember me", "fresh login" required for password/email changes.
- [x] **S-08 · P1 · Security headers** — Flask-Talisman: strict CSP (no `unsafe-inline`; this is why U-14 removes inline styles and handlers), `X-Content-Type-Options`, `Referrer-Policy`, frame protection, HSTS in prod. `Cache-Control: no-store` on every page that shows patient data.
- [x] **S-09 · P0 · Debug off by default** — `app.py:42` defaults `FLASK_DEBUG` to `'true'` (Werkzeug debugger = remote code execution if exposed). Default false; serve with gunicorn; custom 400/403/404/429/500 pages that show a request id, never internals.
- [x] **S-10 · P1 · Input validation layer** — WTForms (or pydantic) for every form and JSON body; max lengths matching columns; enum whitelists; normalized email (lower-case), phone format; reject unknown fields on JSON APIs.
- [x] **S-11 · P1 · Database least privilege** — app connects as a dedicated user with only DML on its schema; migrations run as a separate privileged user; `utf8mb4`; TLS in prod; no `DROP DATABASE/TABLE` convenience scripts outside `tests/`.
- [x] **S-12 · P1 · Account lifecycle** — email verification on signup; password reset via signed expiring token (`itsdangerous`, ≤ 30 min, single use); change password/email requires current password; "log out of other devices"; admin-initiated reset forces change at next login.
- [x] **S-13 · P2 · Sensitive-data handling** — no PHI in logs or error messages; every read of a medical record by a *different* user than the patient writes an audit event; consent checkbox + privacy page at signup; admin "export my data" and "request deletion" workflow (soft-delete + retention note). No compliance claims (D11).
- [x] **S-14 · P1 · Supply chain** — pin + lock dependencies, `pip-audit` in CI, Dependabot, **self-host** Bootstrap/icons/fonts (today three CDNs without Subresource Integrity: jsDelivr, cdnjs, Google Fonts).
- [x] **S-15 · P2 · File upload safety (for F-07 attachments)** — allow-list MIME + extension, sniff magic bytes, size cap, random server-side names, store outside the web root, serve through an authorized route with `Content-Disposition`.

---

## PHASE 3 — Architecture and data model

- [x] **A-01 · P1 · Application factory and layering**
  ```
  hms/
    __init__.py            # create_app(config_name)
    config.py              # DevConfig / TestConfig / ProdConfig
    extensions.py          # db, migrate, login_manager, csrf, limiter, talisman, mail
    models/                # one module per aggregate
    services/              # appointments, billing, admissions, records, accounts, notifications, audit
    policies.py            # object-level authorization
    blueprints/            # auth, public, patient, doctor, admin, billing, api
    forms/                 # WTForms
    templates/ static/
    cli.py                 # create-admin, seed-demo, send-reminders, mark-missed
  migrations/  tests/  docs/  docker/  .github/
  ```
  **Done when:** routes contain no business rules or raw SQL (grep test), only parse input → call service → render.
- [x] **A-02 · P1 · Flask-Migrate baseline** — generate the baseline migration from the *corrected* models; a migration test upgrades an empty DB to head and a DB seeded from the old schema to head (T-07).
- [x] **A-03 · P2 · Config and feature flags** — env-driven settings: timezone (`Asia/Kolkata` default), slot length, cancellation window, reminder lead time, payment gateway, mail backend.
- [x] **A-04 · P2 · Time handling** — store `DATETIME` in the hospital time zone **or** UTC (pick one, document it, and convert only at the edges); one `format_date/time/currency` filter set (en-IN, `₹`).

### Data model changes

- [x] **D-01 · P0 · Typed, relational appointments**
  - **Today:** `date` and `time` strings; `doctor` is a name; `slot` is a status. (`models.py:35-44`)
  - **Target:** `appointment(id, patient_id FK, doctor_id FK, department_id FK, starts_at DATETIME, duration_min, status ENUM, reason TEXT, cancelled_by, cancel_reason, created_at, updated_at, deleted_at)`.
  - **Data migration:** map `appointments.doctor` → `doctors.did` via `user.username`; **duplicates or no-matches go to a `migration_unmatched` report for manual review — never guess.** Parse `time`/`date` with `STR_TO_DATE`; rows that fail to parse are reported, not dropped.
  - **Done when:** all sorting/filtering is done in SQL on `starts_at`; no `strptime` in routes.
- [x] **D-02 · P1 · Status vocabulary** — one enum used by DB, services and UI: `Scheduled → CheckedIn → Completed`; `Scheduled → Cancelled | Missed`. Today's `Attended` maps to `CheckedIn`. UI labels come from one `status_badge` macro (U-04).
- [x] **D-03 · P0 · Double-booking enforced by the schema**
  ```sql
  ALTER TABLE appointments
    ADD COLUMN active_slot_key VARCHAR(64) GENERATED ALWAYS AS (
      CASE WHEN status IN ('Cancelled','Missed') THEN NULL
           ELSE CONCAT(doctor_id, '|', DATE_FORMAT(starts_at, '%Y-%m-%d %H:%i')) END
    ) STORED,
    ADD UNIQUE KEY uq_active_slot (active_slot_key);
  ```
  MySQL has no partial unique indexes; unique indexes allow many NULLs, so cancelled/missed slots free up automatically. The service catches `IntegrityError` → "slot taken". Retire `BookAppointmentSafe`.
  **Done when:** 20 parallel booking attempts for one slot yield exactly 1 success (T-03).
- [x] **D-04 · P0 · Money and invoices** — `DECIMAL` end-to-end (no `float`); `invoice(id, number UNIQUE 'INV-2026-000123', patient_id, appointment_id, admission_id NULL, status ENUM(Draft,Issued,Paid,Void,Refunded), issued_at, due_at, subtotal, tax, discount, total)`, `invoice_item(invoice_id, description, qty, unit_price)`, `payment(id, invoice_id, method, amount, status, gateway_ref, idempotency_key UNIQUE, paid_at, recorded_by)`. Totals are computed from items, never hand-typed.
- [x] **D-05 · P0 · Soft delete and referential safety** — `deleted_at`/`is_active` on user, doctor, appointment, room; `ON DELETE RESTRICT` on all clinical/financial foreign keys; "delete" in the UI means deactivate; a user with history can never be hard-deleted.
- [x] **D-06 · P1 · Departments and doctor profile** — `department` table replaces free-text `dept` (appears in 3 form placeholders, the DDL and the seed data); `doctor(department_id, consultation_fee, qualifications, bio, photo, years_experience)`.
- [x] **D-07 · P1 · Patient profile** — `patient_profile(user_id, dob, blood_group, address, emergency_contact_name/phone, allergies, chronic_conditions)`; widen `phone` to 20.
- [x] **D-08 · P1 · Doctor availability** — `doctor_schedule(doctor_id, weekday, start_time, end_time, slot_minutes)`, `doctor_break`, `doctor_leave(date_from, date_to, reason)`. Slots are **generated server-side** from these rules minus booked appointments (today slot generation lives in browser JS in `book_appointment.html`).
- [x] **D-09 · P1 · Audit events** — `audit_event(id, actor_id NULL, actor_role, action, entity_type, entity_id, before JSON, after JSON, ip, user_agent, request_id, created_at)`; append-only (no UPDATE/DELETE grants); written by a single `audit.record()` helper from services; covers logins, failed logins, role changes, record views/edits, billing, discharge, deletes.
- [x] **D-10 · P1 · Medical records** — `prescription_item(record_id, medicine, dose, frequency, duration, instructions)`; **edits create a new `medical_record_version`** (today `doctor.py:185-191` overwrites silently; clinical records need an amendment history).
- [x] **D-11 · P2 · Indexes** — `(patient_id, starts_at)`, `(doctor_id, starts_at)`, `invoice(patient_id, status)`, `audit_event(entity_type, entity_id, created_at)`; verify with `EXPLAIN` on the dashboard queries.
- [x] **D-12 · P1 · Model ↔ DDL parity test** — fail CI if SQLAlchemy metadata and the migrated database disagree (today: `date`, `time`, `usertype`, `gender`, `ward_type`, `audit_log.timestamp` all differ between `models.py` and `hms.sql`).

---

## PHASE 4 — Design system and UI/UX overhaul

**Evidence this phase fixes (verified):** 4 pages define their own `:root` on top of `base.html` (the booking page uses a blue `--primary:#0d6efd` system; the base uses teal/navy `--hms-*`) · fonts Syne, DM Sans, Inter, Itim · 22 page-level `<style>` blocks across 19 of 24 pages · `index.html` has 4 style blocks + 90 inline `style=` · modals use Bootstrap default blue (`bg-primary`) and a one-off `#2c3e50` while the brand is teal · 55 inline `onclick`, 28 of them on `div/span/tr/li/td` · 11 blocking `confirm()/alert()` (8 + 3) · hard-coded URLs · no pagination · search hidden below the `lg` breakpoint.

- [x] **U-01 · P0 · Design tokens** — `static/css/tokens.css`: color scale + semantic roles (`--color-bg`, `--color-surface`, `--color-text`, `--color-text-muted`, `--color-primary`, `--color-success/warning/danger/info` with `-bg`/`-border` variants), 4-px spacing scale, radius, shadow, z-index, type scale, motion durations. Light + dark via `[data-theme]` and `prefers-color-scheme`. **Done when:** zero hex colors outside `tokens.css` (grep test).
  - **Contrast rules (computed, WCAG 2.x ratios):** the current brand teal `#00c9a7` is **2.12:1** on white — it fails AA both as text and as a background for white text. The navbar *Signup* button does exactly that (`base.html`: `text-white` on `var(--hms-teal)`). Likewise `#f59e0b` amber text (2.15:1), `#ef4444` red text (3.76:1) and `#10b981` green text (2.54:1) fail on white.
  - **Token policy:** keep `#00c9a7` as a *decorative/fill* color only, and pair it with **navy `#0b1d35` text (7.99:1)**. For teal text, links and white-on-color buttons use the darker role colors below. Validate every foreground/background pair in a script (`tools/check_contrast.py`) that fails CI under 4.5:1 (3:1 for large text/UI borders).

    | Role | Light mode | Contrast on white | Dark mode |
    |---|---|---|---|
    | primary (text/button bg, white label) | `#0f766e` | 5.47:1 | `#5eead4` on navy (11.44:1) |
    | accent fill (decorative) | `#00c9a7` + navy text | 7.99:1 (navy on teal) | same |
    | warning text | `#92400e` | 7.09:1 | choose + verify |
    | danger text | `#b91c1c` | 6.47:1 | choose + verify |
    | success text | `#15803d` | 5.02:1 | choose + verify |
    | muted text | `#64748b` (on `#f7f9fc` = 4.51:1, barely passes — darken one step for small text) | 4.76:1 | `#94a3b8` on navy (6.60:1) |
- [x] **U-02 · P1 · Typography** — Syne for display headings only, DM Sans for everything else; **self-hosted** woff2, `font-display: swap`; Inter and Itim removed.
- [x] **U-03 · P1 · Asset pipeline** — vendor Bootstrap 5.3.x CSS/JS and the icon set locally (pick **one** icon library; today Font Awesome 6.4 only), layered CSS (`@layer reset, tokens, base, components, utilities`). No Node build required.
- [x] **U-04 · P0 · Component library (Jinja macros in `templates/components/`)** — `button`, `icon_button`, `status_badge` (single mapping for appointment/invoice/room/admission states), `card`, `stat_card`, `page_header` (title + breadcrumbs + actions), `data_table` (sortable, paginated, responsive, empty + loading + error states), `form_field` (label, hint, error, `aria-describedby`), `csrf_field`, `modal_confirm`, `drawer`, `toast`, `empty_state`, `avatar`, `timeline`, `stepper`, `pagination`, `skeleton`, `kpi_tile`. **Done when:** no page hand-rolls any of these.
- [x] **U-05 · P0 · Layouts and navigation** — `layouts/public.html` (landing/auth) and `layouts/app.html` with a **role-aware sidebar** (collapsible; bottom-sheet/drawer on mobile), topbar (global search, notifications bell, theme toggle, user menu). Remove "Quick Add" modals from the navbar; replace with page-level actions. Real footer (links, version, privacy), accessible contrast.
- [x] **U-06 · P1 · Page-by-page redesign** (details in Appendix C): landing, login, signup, forgot/reset/verify, patient home, booking wizard, appointments (tabs), appointment detail, reschedule, records timeline, bills, payment, profile; doctor today-queue, schedule calendar, patient detail, write-prescription, admissions, availability; admin KPI dashboard, appointments, doctors/patients/staff directories, rooms/beds board, billing, audit log, settings; 403/404/500.
- [x] **U-07 · P1 · Replace `confirm()`/`alert()`** — accessible `modal_confirm` component (focus trap, Esc, returns focus); inline field validation; irreversible actions require typing the entity name.
- [x] **U-08 · P0 · Accessibility (target WCAG 2.2 AA)**
  - Make interactive things real controls: the 28 clickable `div/span/tr/li/td` (stat cards, doctor cards, payment mode cards, filters) become `<button>`/`<a>`/radio inputs.
  - Visible `:focus-visible` rings, skip-to-content link, landmarks, one `<h1>` per page, labels/`aria-describedby` for every field, color contrast ≥ 4.5:1 (fixes B-25), toasts in an `aria-live` region.
  - `prefers-reduced-motion`: disable the shimmering brand animation, slide-in toasts and hover-lift transforms.
  - Never convey status by color alone (icon + text in every badge).
  - **Done when:** axe-core reports 0 serious/critical issues on every key page (T-05) and the whole booking flow works by keyboard only.
- [x] **U-09 · P1 · Responsive** — mobile-first; tables collapse to stacked cards < 768 px; touch targets ≥ 44 px; search reachable on mobile; verified at 360, 768, 1280, 1920 px.
- [x] **U-10 · P1 · UX states and feedback** — skeleton loaders, meaningful empty states with a primary CTA, inline error states, double-submit prevention (disable + spinner), unsaved-changes warning on long forms, success pages that say what happens next, undo for reversible actions.
- [x] **U-11 · P2 · Admin data visualization** — appointments per day, revenue (collected vs pending), bed occupancy, no-show rate, top departments; self-hosted Chart.js (or inline SVG) with a data-table fallback for screen readers; date-range filter; every chart cites its query in `docs/analytics.md`.
- [x] **U-12 · P2 · Print** — `@media print` styles for invoice, receipt, prescription, discharge summary (hide chrome, A4, letterhead from settings).
- [x] **U-13 · P2 · Microcopy and localization** — plain, calm language (remove "Premium", "Pro Max", "Secure Logout", "Enter Admin Panel" marketing tone from app chrome); all strings through a single place so i18n is possible later; en-IN date/number formats; `₹` via filter.
- [x] **U-14 · P0 · Zero inline CSS/JS** — remove every `<style>`, `style=` and `onclick=`; page logic in `static/js/pages/*.js` using `data-*` attributes and event delegation. **Done when:** CSP without `unsafe-inline` (S-08) passes on every page.
- [x] **U-15 · P2 · Brand and meta** — SVG logo + favicon set, per-page `<title>`, Open Graph tags, error-page illustrations, consistent iconography.
- [x] **U-16 · P2 · Visual QA artifacts** — Playwright screenshots for every key page × 3 breakpoints × 2 themes into `docs/screenshots/` (used by the README).

---

## PHASE 5 — Core features to finish the product

- [x] **F-01 · P1 · Reschedule appointment** — replaces orphan `edit.html`; respects availability and the unique-slot rule; cutoff window (default ≥ 2 h before start, configurable); keeps history; notifies both parties.
- [x] **F-02 · P1 · Global search with typeahead** — staff: patients by name/email/phone (authorization-scoped; doctors only see patients they have treated); patients: doctors by name/department/specialty. Debounced, keyboard navigable, works on mobile.
- [x] **F-03 · P1 · Availability and slots API** — `GET /api/v1/doctors/<id>/slots?date=YYYY-MM-DD` generated from D-08; replaces `POST /get_booked_slots` and the client-side slot generation.
- [x] **F-04 · P0 · Appointment state machine** — allowed transitions only; cancel needs actor + reason; "Missed" is set automatically after a grace period (R-04) or by the doctor; every transition audited; invalid transitions return 409 with a clear message.
- [x] **F-05 · P1 · Notifications** — email (SMTP in prod, Mailpit in dev) for booking confirmation, 24-h reminder, reschedule/cancel, invoice issued, payment receipt, password reset/verification; in-app notification center with unread count; per-user preferences; all sending goes through a `Notifier` interface and an outbox table so a failed email never fails the request.
- [x] **F-06 · P0 · Billing and payments**
  - Itemized invoices (consultation, room-days, procedures, medicines), numbering, discount/tax fields, void and refund flows.
  - `PaymentGateway` interface: `MockGateway` (default, deterministic, test-friendly) and a Razorpay **test-mode** adapter selected by env. Server verifies payment signatures/webhooks (HMAC), uses idempotency keys, never trusts the client's "paid" claim.
  - **Cash** is recorded only by authorized staff (admin/billing/receptionist), with the staff member stored on the payment.
  - Patient pages: invoice list, invoice detail, pay, receipt (print/PDF). Admin: collections, outstanding, refunds, daily reconciliation CSV.
  - **Done when:** the "patient marks own invoice Paid" path (B-18) is impossible and covered by a test.
- [x] **F-07 · P1 · Clinical records** — structured prescription (D-10), printable prescription, patient timeline across visits, lab/report attachments (S-15), amendment history, "visible to patient" control, follow-up date that can create a follow-up appointment.
- [x] **F-08 · P1 · Inpatient module** — bed/room board (grid by ward with live status), admit with expected stay, transfer room, discharge summary, accurate room billing (B-07), maintenance state with reason; one active admission per room enforced by schema (B-13).
- [x] **F-09 · P1 · Admin operations** — KPI dashboard (U-11), CSV export (appointments, invoices, audit), user directory with deactivate/reactivate and role change (audited), department CRUD, settings page (hospital name/logo, timezone, slot length, cancellation window, default fee), audit-log viewer with filters (actor, action, entity, date) and pagination.
- [x] **F-10 · P2 · Receptionist role** — book on behalf of a patient, check-in, collect cash, view the day's queue. Delivered as a permission set on the RBAC matrix (S-05), not new `if` branches.
- [x] **F-11 · P2 · Versioned JSON API + OpenAPI docs** at `/api/v1` for the endpoints the UI already needs (slots, search, notifications, appointments); same auth, CSRF and rate-limit rules; generated docs at `/api/docs`.
- [x] **F-12 · P0 · Server-side pagination, sorting, filtering** — default 20 per page on every list (admin appointments, patients, doctors, billing, audit log, patient history); state in the query string so views are linkable; replaces client-side filtering of the entire dataset (`appointment_history.html:380-386` reads `?filter=` in JS and filters rows already sent to the browser; `base.html` links to `/dashboard?filter=Pending` relying on that).
- [ ] **F-13 · P3 · Stretch (only if everything above is done):** dependents (book for a family member), tele-consult link on an appointment, pharmacy/lab order tracking, multi-branch.

---

## PHASE 6 — Reliability and observability

- [x] **R-01 · P1 · Structured logging** — JSON logs with `request_id`, user id (not name/email), route, latency, status; no PHI; request id also shown on error pages.
- [x] **R-02 · P1 · Health endpoints** — `/healthz` (process up), `/readyz` (DB reachable, migrations at head).
- [x] **R-03 · P1 · Error handling** — global handlers for 400/403/404/409/429/500; map `IntegrityError`/`OperationalError` to friendly messages; transactions rolled back in one place (`teardown`/service boundary).
- [x] **R-04 · P1 · Scheduled jobs** — `flask send-reminders` (every 15 min) and `flask mark-missed` (every 10 min) run by APScheduler or cron; idempotent and safe to run twice.
- [x] **R-05 · P2 · Backups and restore** — documented `mysqldump` backup + restore drill; migration downgrade tested at least one step.
- [x] **R-06 · P2 · Production serving** — gunicorn, `ProxyFix` behind a reverse proxy, `SERVER_NAME`/trusted hosts, gzip + long-cache for hashed static assets.
- [x] **R-07 · P3 · Error monitoring hook** — optional Sentry DSN via env; PHI scrubbing before send.

---

## PHASE 7 — Testing and CI/CD

- [ ] **T-01 · P0 · Test layout** — `tests/unit` (services, policies, state machine), `tests/integration` (real MySQL via Docker/CI service — **not SQLite**, because the unique-slot index, generated column and row locks are MySQL behavior), `tests/e2e` (Playwright). Coverage gate: ≥ 85 % on `services/` and `policies.py`.
- [ ] **T-02 · P1 · Fixtures** — `factory_boy` factories for every model; per-test transaction rollback; frozen clock fixture for time-dependent logic.
- [ ] **T-03 · P0 · Concurrency tests** — N parallel bookings for one slot → exactly one succeeds; double-submitted discharge → exactly one invoice; two admissions into one room → exactly one succeeds; duplicate payment webhook → one payment.
- [ ] **T-04 · P0 · Authorization matrix** — generated from the Flask URL map: every route × {anonymous, patient (owner), patient (other), doctor (owner), doctor (other), admin} → expected status (200/302/403/404). Fails the build if a new route has no expectation.
- [ ] **T-05 · P1 · E2E + accessibility** — Playwright: signup → verify → book → doctor check-in → write record → invoice → pay (mock gateway) → receipt; admin discharge flow; axe-core scan on each key page; keyboard-only run of the booking wizard.
- [ ] **T-06 · P1 · CI (GitHub Actions)** — jobs: lint (`ruff`, `black --check`, `djlint`), type-check (`mypy` on `services/`), tests with MySQL service container, `pip-audit`, Docker build; required status checks on `main`; `pre-commit` config mirrors CI.
- [ ] **T-07 · P1 · Migration tests** — empty DB → head; old-schema fixture with representative rows → head with the unmatched-report assertions from D-01.
- [ ] **T-08 · P1 · Link crawler** — render every page as every role and assert every `href`/`form action` resolves (would have caught B-01/B-02/B-03).
- [ ] **T-09 · P2 · Performance budget** — dashboard queries ≤ 10 per request (assert with a query counter); no N+1 on list pages.

---

## PHASE 8 — Packaging, deployment, documentation

- [ ] **P-01 · P1 · Docker** — multi-stage `Dockerfile` (non-root, gunicorn, healthcheck); `docker-compose.yml` with app, MySQL 8, Mailpit, optional Redis; `make up | down | test | lint | seed | migrate`.
- [ ] **P-02 · P2 · Deployment guide** — env-var table, first-run checklist (migrate → create-admin → settings), one worked example on a free-tier host, backup/restore notes.
- [ ] **P-03 · P1 · Documentation set** — `README.md` (what/why, screenshots, quickstart, architecture + ER diagrams in Mermaid, feature list by role, testing, roadmap), `docs/ARCHITECTURE.md`, `docs/SECURITY.md` (threat model, what is and is not claimed), `docs/billing.md` (business rules), `docs/analytics.md`, `docs/adr/000N-*.md` for decisions D1–D11, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE`.
- [ ] **P-04 · P2 · Demo data** — Faker-based `flask seed-demo` producing ~6 months of realistic appointments, records, invoices and admissions (dev only; random passwords printed once).
- [ ] **P-05 · P2 · Release** — tag `v1.0.0`, changelog, release notes with screenshots.

---

## Appendix A — Target authorization matrix (starting point for T-04)

| Capability | Anonymous | Patient | Doctor | Receptionist | Admin |
|---|---|---|---|---|---|
| Browse doctors, landing | ✓ | ✓ | ✓ | ✓ | ✓ |
| Book / reschedule / cancel own appointment | – | ✓ | – | on behalf | ✓ |
| View own appointments & records | – | ✓ | – | – | audit only |
| View patient records | – | own | **only patients with an appointment with this doctor** | – | audited access |
| Check-in / mark missed | – | – | own appointments | ✓ | ✓ |
| Write / amend record | – | – | own appointments (amendment kept) | – | – |
| Admit / discharge | – | – | own admissions | – | ✓ |
| View own invoices / pay online | – | ✓ | – | – | ✓ |
| Record cash payment, void, refund | – | – | – | cash only | ✓ |
| Manage users, departments, rooms, settings | – | – | – | – | ✓ |
| View audit log | – | – | – | – | ✓ |

## Appendix B — Status vocabulary (single source, used by DB, services, UI)

| Entity | States |
|---|---|
| Appointment | `Scheduled`, `CheckedIn`, `Completed`, `Missed`, `Cancelled` |
| Invoice | `Draft`, `Issued`, `Paid`, `Void`, `Refunded` |
| Payment | `Pending`, `Succeeded`, `Failed`, `Refunded` |
| Room | `Available`, `Occupied`, `Maintenance` |
| Admission | `Admitted`, `Discharged` |

## Appendix C — Page-by-page UX checklist

For each page: layout from `layouts/app.html` · page header with breadcrumbs · all components from the library · empty/loading/error states · keyboard + screen-reader pass · mobile layout · light/dark · print (where relevant) · screenshot saved.

- **Landing:** value proposition, department list from DB, doctor highlights (real data), clear "Book appointment" CTA, trust/security note without compliance claims.
- **Auth:** single-column forms, show/hide password, inline validation, strength meter, forgot/reset/verify flows, lockout message that does not reveal whether the account exists.
- **Patient home:** next appointment card, outstanding bills, recent records, quick actions.
- **Booking wizard (4 steps with stepper):** department → doctor (cards with fee, next availability) → date/time (server slots) → reason + review → confirmation with add-to-calendar (`.ics`).
- **Appointments:** tabs Upcoming / Past / Cancelled, server pagination, detail drawer, reschedule/cancel with reason.
- **Records:** timeline across visits, printable prescription, attachments.
- **Doctor today-queue:** one-glance queue (waiting / in room / done), keyboard shortcuts for check-in, "pending prescription" lane, patient history side panel.
- **Admin dashboard:** KPI tiles with deltas vs previous period, charts with table fallback, "needs attention" list (unpaid > 7 days, rooms in maintenance, doctors with no schedule).
- **Rooms/beds:** ward-grouped board, color + icon + text status, occupant and expected discharge on hover/focus.
- **Billing:** filters (status, date, patient), totals bar, row actions behind a menu, export CSV.
- **Audit log:** filters + pagination + "view entity" deep links; read-only.

## Appendix D — Explicitly out of scope unless the owner asks

Insurance/claims, HL7/FHIR integration, ABDM integration, e-signature, native mobile apps, multi-tenant SaaS, real-money production payments, any statement that the system is "HIPAA/DPDP compliant".
