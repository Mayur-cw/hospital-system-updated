# Phase 3 — Architecture & Data Model Refactor

**Date:** November 17, 2026  
**Status:** Completed  
**Branch:** `phase-3-arch-datamodel`  
**Gate Status:** Green (`pytest` 22 passed on SQLite & native MySQL 9.6, `pip-audit` zero vulnerabilities, `ruff` clean)

---

## 1. What Changed (with IDs)

* **A-01 (Application Factory & Package Layering):** Migrated from monolithic script layout to modular `hms/` package structure (`create_app` factory in `hms/__init__.py`, `hms/extensions.py`, modular `hms/models/`, `hms/services/`, and `hms/policies.py`). Application routes now parse input, authorize via policies, delegate business logic to services, and render.
* **A-02 (Flask-Migrate Baseline):** Initialized Alembic migrations in `migrations/` and generated the baseline migration (`18fc14f5fe1c_baseline_schema.py`) targeting the corrected domain schema across 17 tables and indexes. Upgraded native MySQL `hms_test` database to head.
* **A-03 (Config & Regional Defaults):** Added environment-driven scheduling and clinical settings: `HOSPITAL_TIMEZONE` (`Asia/Kolkata` default), `SLOT_DURATION_MINUTES` (30 min default), `CANCELLATION_WINDOW_HOURS` (2 hours default), `REMINDER_LEAD_HOURS` (24 hours default), and `PAYMENT_GATEWAY` (`mock`).
* **A-04 (Time Handling & Indian Currency Formatting):** Established UTC persistence in the database with conversion at display edges to Indian Standard Time (`Asia/Kolkata`). Implemented custom Jinja formatting filters (`format_currency` for `₹` with Indian lakh/crore commas, `format_date`, `format_time`, `format_datetime`).
* **D-01 (Typed, Relational Appointments):** Replaced legacy free-text strings with relational `Appointment` model: foreign keys (`patient_id`, `doctor_id`, `department_id`), typed `starts_at DATETIME`, `duration_min INT`, and status enum (`Scheduled`, `CheckedIn`, `Completed`, `Cancelled`, `Missed`).
* **D-03 (Double-Booking Enforced by Schema):** Added MySQL STORED generated column `active_slot_key` with a UNIQUE index `uq_active_slot`. When appointments are cancelled or missed, the key evaluates to `NULL`, automatically freeing the slot without application-level race conditions. Verified with 20 parallel threads competing on native MySQL 9.6.
* **D-04 (Money and Invoices):** Replaced all floating-point calculations with `DECIMAL(10,2)`. Built relational `Invoice`, `InvoiceItem`, and `Payment` models with unique invoice numbering (`INV-YYYY-XXXXXX`) and payment idempotency keys.
* **D-05 (Soft Delete & Referential Safety):** Added `SoftDeleteMixin` (`is_active`, `deleted_at`) and `ON DELETE RESTRICT` on clinical and financial foreign keys to prevent cascading data loss.
* **D-06 & D-07 (Departments, Doctor & Patient Profiles):** Introduced normalized `Department` model and extended `Doctor` and `PatientProfile` models (date of birth, blood group, emergency contact, allergies, chronic conditions).
* **D-08 (Doctor Availability Engine):** Implemented `DoctorSchedule`, `DoctorBreak`, and `DoctorLeave` models with server-side `AvailabilityService.get_available_slots()`.
* **D-09 & D-11 (Append-Only Audit Log & Composite Indexes):** Created append-only `AuditEvent` with JSON payload capture, and added composite indexes (`ix_patient_starts_at`, `ix_doctor_starts_at`, `ix_invoice_patient_status`, `ix_audit_entity_created`).
* **D-10 (Versioned Medical Records):** Built clinical records with structured `PrescriptionItem` models and historical amendment tracking via `MedicalRecordVersion`.
* **D-12 (Model ↔ DDL Parity Test):** Added automated integration test `tests/integration/test_ddl_parity.py` comparing SQLAlchemy metadata directly against migrated MySQL 9.6 database.

---

## 2. Why This Approach (Design Trade-offs & Decisions)

### Choice 1: Database-Enforced Slot Uniqueness vs Application-Level Locking
* **Alternative A (Considered):** `SELECT ... FOR UPDATE` before inserting an appointment.
  * *Downside:* In MySQL InnoDB under `REPEATABLE READ`, selecting non-existent rows can lead to gap locks, deadlocks, and silent race conditions under high concurrency.
* **Alternative B (Chosen — D-03):** MySQL STORED Generated Column `active_slot_key` with a `UNIQUE` index:
  ```sql
  active_slot_key VARCHAR(64) GENERATED ALWAYS AS (
    CASE WHEN status IN ('Cancelled','Missed') THEN NULL
         ELSE CONCAT(doctor_id, '|', DATE_FORMAT(starts_at, '%Y-%m-%d %H:%i')) END
  ) STORED UNIQUE
  ```
  * *Why chosen:* Relational databases excel at enforcing mathematical uniqueness. Because SQL standard allows multiple `NULL` values in a unique index, cancelled or missed appointments automatically release the slot without deleting rows or requiring locks.

### Choice 2: Financial Precision — `DECIMAL(10,2)` vs `float`
* **Alternative A (Legacy):** Python `float` and SQL `FLOAT` for billing amounts.
  * *Downside:* Binary floating-point representation cannot accurately represent base-10 decimals (e.g. `0.1 + 0.2 = 0.30000000000000004`). In healthcare invoicing, fractional rounding errors accumulate into auditing discrepancies.
* **Alternative B (Chosen — D-04):** `DECIMAL(10, 2)` end-to-end via Python `decimal.Decimal` and SQLAlchemy `db.Numeric(10, 2)`.
  * *Why chosen:* Exact financial precision, compliance with statutory bookkeeping rules, and mathematical stability across taxes and discounts.

### Choice 3: Service Layer vs Heavy Route Handlers
* **Alternative A (Legacy):** Routes directly executing SQL queries, computing charges, and modifying database tables.
  * *Downside:* Untestable without full HTTP requests, duplicated business logic (e.g. separate, inconsistent discharge implementations in `doctor.py` and `admin.py`), and risk of incomplete transactions.
* **Alternative B (Chosen — A-01):** Dedicated Service Layer (`hms/services/`).
  * *Why chosen:* Routes become thin HTTP adapters (parse JSON/form -> check policy -> call service -> return response). Business logic is unit-testable in isolation and shared consistently across web views, APIs, and background CLI jobs.

---

## 3. Concepts to Understand

1. **Why a UNIQUE Index Beats Check-Then-Insert (Time-of-Check to Time-of-Use):**
   When two users click "Book Slot" at the exact same millisecond, both processes query the database (`SELECT COUNT(*)`), see 0 bookings, and both proceed to `INSERT`. A database-level `UNIQUE` constraint guarantees that the database engine itself atomizes the check and write inside the B-Tree index, rejecting the second attempt with an `IntegrityError`.
2. **Idempotency Keys in Payment Processing:**
   An idempotency key is a unique token generated by the client for a specific transaction. If a network timeout occurs and the user's browser retries the payment request, the server recognizes the duplicate idempotency key and returns the existing receipt without charging the card or creating a duplicate invoice.
3. **Soft Delete vs Hard Delete in Healthcare Systems:**
   In clinical software, historical records (prescriptions, consultations, admissions) must never be permanently erased (`DELETE FROM ...`) because medical history informs future diagnoses and medico-legal accountability. Soft deletion sets `is_active = False` and `deleted_at = NOW()`, hiding the record from active UI lists while preserving relational integrity.

---

## 4. Try It Yourself

1. **Test Concurrency Protection Against Native MySQL:**
   Run the 20-thread parallel race test against MySQL 9.6:
   ```bash
   .venv312/bin/pytest -s tests/integration/test_concurrency_mysql.py
   ```
   *Observation:* Observe `Concurrency Results: 1 Success, 19 Rejected, 0 Errors`. Exactly 1 appointment was written.

2. **Verify Database ↔ Model Parity:**
   Run the DDL inspector comparing SQLAlchemy metadata against the live MySQL schema:
   ```bash
   .venv312/bin/pytest tests/integration/test_ddl_parity.py
   ```

3. **Check Financial Formatting:**
   Open Python in the virtualenv:
   ```python
   from hms.filters import format_currency
   from decimal import Decimal
   print(format_currency(Decimal('152450.75'))) # Output: ₹ 1,52,450.75
   ```

---

## 5. Self-Check Questions

1. *How does MySQL treat `NULL` values inside a `UNIQUE` index, and how does that make appointment cancellation automatic?*
2. *Why should currency calculations never use `float` in Python or MySQL?*
3. *What prevents a malicious user from discharging a patient twice and generating double invoices?*
4. *Where does object-level authorization live in the new architecture, and what is its default response when a rule is not explicitly matched?*
5. *Why is `created_at` stored in UTC in the database even though Hedgewar Hospital operates in `Asia/Kolkata`?*
