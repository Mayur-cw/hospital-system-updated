# ADR-0002: Data Layer and Stored Procedure Evolution
**Date:** 2026-11-17  
**Status:** ACCEPTED  
**Deciders:** Staff Engineer, Security Engineer, Clinical-Workflow Analyst

## Context
The legacy database schema in `hms.sql` has three critical problems:
1. **Destructive DDL and Deletes**: Uses `DROP TABLE IF EXISTS` and `ON DELETE CASCADE` across sensitive clinical and financial records (`appointments`, `medical_records`, `billing`, `admissions`). Admin routes invoke `db.session.delete()`, permanently purging historical records.
2. **Denormalized Scheduling**: The `appointments` table stores `doctor`, `dept`, `date`, `time`, and `slot` as loose `VARCHAR` strings rather than normalized foreign keys and typed timestamps.
3. **Stored Procedure Locking Hazards**: The `BookAppointmentSafe` procedure executes `SELECT COUNT(*) ... FOR UPDATE` without a database unique constraint on `(doctor_id, date, time)`, creating a race hazard under concurrent bookings. Furthermore, `CALL BookAppointmentSafe` hardcodes dependency on MySQL, preventing portable testing on SQLite or staging on PostgreSQL.

## Decision
1. **Additive Schema Migration**:
   - Abolish destructive `DROP TABLE` and `ON DELETE CASCADE` in application workflows.
   - Maintain historical permanence: records are soft-cancelled or archived with status transitions, never physically purged.
   - Introduce database-enforced unique constraints:
     `UNIQUE (doctor_id, appointment_date, appointment_time)` for active (non-cancelled) slots.
     `UNIQUE (bed_id)` for active admissions.
2. **Abstract Concurrency into Domain Services**:
   - Replace direct raw SQL `CALL BookAppointmentSafe` calls with a Python `SchedulingService.book_appointment()` domain service that uses transactional row locking (`with_for_update()`) and database-level unique constraints.
   - This works consistently across SQLite (for zero-config local testing and development), MySQL 8+, and PostgreSQL.
3. **Structured Timestamps & Normalization**:
   - Store dates and times with proper types (`Date`, `Time`, and UTC `DateTime`).
   - Store normalized `doctor_id` foreign key referencing `Doctors.did` (or `User.id`).

## Consequences
- **Positive**:
  - Invariant safety guaranteed by database constraints, preventing double bookings under high concurrency.
  - Portability across development (SQLite) and production (MySQL/PostgreSQL).
  - Clinical and financial audit trail permanently preserved.
- **Negative / Tradeoffs**:
  - Legacy records with denormalized strings require a backwards-compatible getter or mapping adapter during transition.
