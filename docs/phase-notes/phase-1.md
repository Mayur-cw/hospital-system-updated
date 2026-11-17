# Phase 1 — Bug Fixes & Data Integrity Hardening

**Date:** November 17, 2026  
**Status:** Completed  
**Branch:** `phase-1-remaining-bugs`  
**Gate Status:** Green (`pytest` 35 passed across SQLite & native MySQL 9.6, `pip-audit` zero vulnerabilities, `ruff` clean)

---

## 1. What Changed (with Change IDs)

* **B-01 (Create Doctor/Admin Routes):** Updated `base.html` and admin staff creation forms to target blueprint prefix `url_for('admin.add_staff')` resolving previous 404 errors.
* **B-02 (Navbar Global Search):** Created `main.search` endpoint (`GET/POST /search`) querying doctors, departments, patients, and rooms; updated `base.html` search bar to remain visible and responsive across all viewports.
* **B-03 (Admin Breadcrumbs & Dashboard Navigation):** Standardized all admin navigation links to `url_for('admin.admin_dashboard')`, eliminating dead `/admin` and `/admin_dashboard` links.
* **B-04 (Unified Invoicing & Receipts):** Standardized invoice and receipt views (`patient.view_invoice`, `patient.view_receipt`, `admin.view_invoice`, `admin.view_receipt`) protected by `can_view_invoice` policies.
* **B-05 & F-01 (Appointment Reschedule):** Implemented `@patient_bp.route('/reschedule/<id>')` and `@patient_bp.route('/edit/<id>')` backed by `AppointmentService.reschedule` with 2-hour cutoff validation, double-booking prevention, and audit event recording.
* **B-06 (Unified Inpatient Discharge Flow):** Consolidated disparate doctor and admin discharge paths into `AdmissionService.discharge` with pessimistic locking (`with_for_update()`), single invoice generation, room status release, and audit trail.
* **B-07 (Room-Day Billing Calculation):** Fixed stay duration under-billing in `BillingService.create_inpatient_invoice` using started 24-hour blocks `max(1, math.ceil(stay_seconds / 86400.0))` with Decimal arithmetic and dynamic departmental room rates (documented in `docs/billing.md`).
* **B-08 & B-09 (Date & Time Relational Sorting):** Removed lexicographical text sorting of dates and 12-hour strings ('01:00 PM' vs '09:00 AM'); all schedules now sort via typed `Appointment.starts_at DATETIME`.
* **B-10 (`get_booked_slots` API Guard):** Added payload validation and graceful error responses in `patient.get_booked_slots` preventing crashes on invalid or missing JSON.
* **B-11 (Booking Error Isolation):** Isolated `SlotAlreadyBookedError` specifically in `AppointmentService.book()`; unexpected errors return structured messages with unique request IDs rather than swallowing exceptions.
* **B-12 (`add_record` Authorization & Safe Reporting):** Added doctor ownership validation in `doctor.add_record` and sanitised error messages to prevent internal database detail leakage.
* **B-13 (Room Allocation Race Prevention):** Applied row-level locking (`with_for_update()`) in `AdmissionService.admit` to prevent concurrent admissions to the same bed.
* **B-14 (Doctor Relational Decoupling):** Replaced legacy username string matching in appointments with foreign key `doctor_id`, preventing schedule corruption when a doctor is renamed.
* **B-15 (Admin Validation Holes):** Whitelisted user roles (`Admin`, `Doctor`), added email uniqueness pre-commit checks, and enforced minimum password length.
* **B-16 (Room Form Validation):** Added server-side whitespace stripping, positive Decimal daily rate enforcement, and ENUM validation for ward types (`General`, `ICU`, `VIP`, `Maternity`).
* **B-17 (Appointment State Transition Guards):** Enforced finite state machine rules preventing cancellation of `Completed`, `Attended`, or `Missed` appointments.
* **B-18 (Cash Self-Marking Prevention & Online Payment):** Prohibited patients from self-clearing invoices as `Cash` online; online payments flow through `BillingService.record_payment` with unique idempotency keys.
* **B-19 (Soft Deletes vs Cascading Data Loss):** Migrated hard deletes to soft deactivations (`is_active = False, deleted_at = now()`) across users, doctors, rooms, and appointments.
* **B-20 (N+1 Query & Table Scan Elimination):** Replaced `MedicalRecord.query.all()` table scans with targeted ID queries, and precomputed appointment counts in `admin_patients` via single aggregated SQL queries.
* **B-21 (Audit Logging Integrity):** Replaced incomplete MySQL triggers with application-level `AuditEvent` logging capturing actor, entity, before/after JSON snapshots, and IP addresses.
* **B-22 (Profile Re-Authentication):** Enforced current password verification in `auth.profile` before email or password modifications are accepted.
* **B-23 (Phone Column Width):** Widened user phone column to `VARCHAR(20)` accommodating international dialing prefixes.
* **B-24 & B-25 (UI Toast & Accessible Footer):** Standardized toast dismissal attributes and modernized the footer with accessible contrast, working links, and Hedgewar Hospital branding.

---

## 2. Design Trade-offs & Decisions

### Choice 1: Started 24-Hour Blocks vs Fractional Day Billing
* **Alternative A (Legacy):** `delta.days` integer division, which billed a 47-hour hospital stay as only 1 day.
* **Alternative B (Chosen — B-07):** Started 24-hour blocks `max(1, math.ceil(total_seconds / 86400.0))`.
  * *Why chosen:* Matches standard hospital inpatient billing standards where occupying a bed for any portion of an inpatient calendar block incurs room charges.

### Choice 2: Online Payment Guard vs Permissive Self-Service
* **Alternative A (Legacy):** Patients could choose `payment_mode=cash` in web forms and immediately mark their own hospital bill as "Paid".
* **Alternative B (Chosen — B-18):** Web forms restrict patients to electronic payment methods (UPI, Card, NetBanking, Mock Gateway) with transaction tracking and idempotency keys. Physical counter cash can only be settled by authorized hospital cashiers and admin staff.

### Choice 3: Soft Deletes vs Hard Foreign Key Cascades
* **Alternative A (Legacy):** `ON DELETE CASCADE` deleted all clinical records, prescription histories, and billing invoices whenever an admin deleted a user or doctor.
* **Alternative B (Chosen — B-19 & D-05):** `SoftDeleteMixin` deactivates records (`is_active = False, deleted_at = UTC`) while preserving complete medical records, historical invoices, and audit logs. Foreign keys on clinical and billing tables use `ON DELETE RESTRICT`.

---

## 3. Automated Test Verification

All fixes are verified by automated tests in `tests/unit/test_phase1_remaining_bugs.py` and `tests/unit/test_smoke_characterization.py`:
- `test_b02_navbar_search_route_and_results` (PASSED)
- `test_b05_appointment_reschedule_flow` (PASSED)
- `test_b07_room_day_billing_started_24h_blocks` (PASSED)
- `test_b08_b09_appointment_datetime_sorting` (PASSED)
- `test_b11_booking_safe_error_isolation` (PASSED)
- `test_b12_add_record_ownership_and_safe_errors` (PASSED)
- `test_b13_room_allocation_concurrency_guard` (PASSED)
- `test_b14_doctor_rename_does_not_orphan_appointments` (PASSED)
- `test_b15_admin_create_staff_validation` (PASSED)
- `test_b16_room_form_validation` (PASSED)
- `test_b17_appointment_state_transition_guards` (PASSED)
- `test_b18_patient_cannot_self_mark_cash_paid` (PASSED)
- `test_b19_soft_delete_preserves_clinical_records` (PASSED)
- Total test suite: 35 passing tests (0 failures, 0 xfails).
