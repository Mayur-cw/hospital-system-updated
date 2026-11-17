# ADR 0011: Composite Indexing & Strict Performance Budget (D-11)

## Status
Accepted

## Context
High-volume hospital clinics face database slowdowns if patient dashboards and scheduling queries perform unindexed full table scans or suffer from N+1 query loops when rendering relationships (such as patient names and departments).

## Decision
1. **Targeted Composite Indexes:**
   - `ix_doctor_starts_at`: `(doctor_id, starts_at)` on `appointments`.
   - `ix_patient_starts_at`: `(patient_id, starts_at)` on `appointments`.
   - `ix_in_app_notification_user_unread`: `(user_id, is_read)` on `in_app_notification`.
2. **Eager Loading Optimization:**
   All dashboard and queue queries employ SQLAlchemy `joinedload` or `selectinload` to fetch user profiles, departments, and doctor details in 1 or 2 queries instead of $1 + N$ queries.
3. **Performance Budget Assertion:**
   A test suite (`tests/unit/test_performance_budget.py`) monitors query counters on every request and fails CI if any dashboard route executes more than 10 SQL queries.

## Consequences
- Deterministic sub-50ms query response times.
- Zero N+1 query regressions across all four role portals.
