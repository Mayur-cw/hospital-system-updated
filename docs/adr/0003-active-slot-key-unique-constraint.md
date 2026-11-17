# ADR 0003: Double-Booking Prevention via MySQL Generated Column & Unique Index (D-03)

## Status
Accepted

## Context
High-concurrency appointment booking previously permitted race conditions where two simultaneous requests could book the same doctor at the exact same minute. MySQL lacks partial unique indexes (e.g. `WHERE status != 'Cancelled'`).

## Decision
We implemented a stored generated column `active_slot_key` on the `appointments` table:
```sql
active_slot_key VARCHAR(64) GENERATED ALWAYS AS (
  CASE WHEN status IN ('Cancelled', 'Missed') THEN NULL
       ELSE CONCAT(doctor_id, '|', DATE_FORMAT(starts_at, '%Y-%m-%d %H:%i')) END
) STORED,
UNIQUE KEY ix_appointments_active_slot_key (active_slot_key)
```
In MySQL, multiple `NULL` values are permitted in unique indexes. When an appointment is scheduled or checked in, `active_slot_key` evaluates to `doctor_id|YYYY-MM-DD HH:MM`, preventing any parallel collision. When cancelled or missed, it transitions to `NULL`, automatically freeing the slot.

## Consequences
- Guaranteed zero double-bookings at the storage engine level.
- Tested and verified under 20 parallel threads in `tests/integration/test_concurrency_mysql.py`.
- Graceful error mapping in `hms/__init__.py`: maps duplicate entry `IntegrityError` to HTTP 409 Conflict.
