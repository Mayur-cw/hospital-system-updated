# ADR-0003: Centralized RBAC and Resource-Level Authorization
**Date:** 2026-11-17  
**Status:** ACCEPTED  
**Deciders:** Security Engineer, Staff Engineer, QA Lead

## Context
The legacy application implements role checks in an ad-hoc manner inside route functions:
- Some routes check `current_user.usertype == 'Admin'`.
- Some check `current_user.usertype == 'Doctor'`, but fail to verify whether the doctor is assigned to the specific appointment or patient (e.g., `doctor.mark_missed`, `doctor.mark_attended`, `doctor.add_record`, `doctor.discharge_patient`). Any doctor could alter another doctor's appointments, write unauthorized charts, or discharge unrelated admissions.
- Some routes check user string matching (`appointment.doctor.lower() == current_user.username.lower()`), which is fragile.
- Several routes permit cross-role access (e.g., `patient.booking_success` allows any doctor to view any patient's booking).

## Decision
Implement a **Centralized Policy Engine** (`app.core.authorization`):
1. **Role-Based Access Control (RBAC)**:
   - Introduce `@require_roles(*roles)` decorator that validates session role against an explicit allowlist.
   - Deny by default: unauthenticated or unauthorized requests are immediately aborted with HTTP 403 / flash error, and logged to the security audit trail.
2. **Object-Level / Care-Team Relationship Authorization**:
   - Helper policy functions:
     `can_access_appointment(user, appointment)`
     `can_modify_appointment(user, appointment)`
     `can_chart_encounter(user, appointment)`
     `can_access_invoice(user, billing)`
     `can_discharge_admission(user, admission)`
   - Object authorization verifies:
     - Admin: full operational access, but no silent clinical chart edits.
     - Doctor: access restricted to assigned appointments, admitted patients, or explicit cross-cover.
     - Patient: access strictly scoped to `record.user_id == current_user.id`.
     - Cashier: access scoped to invoice and payment processing.
3. **Automated Regression Suite**:
   - Dedicated security test suite (`tests/test_authorization.py`) verifying all negative test cases (T-AUTH-001 through T-AUTH-005, T-TENANT-001) to prevent BOLA/IDOR regressions.

## Consequences
- **Positive**:
  - Eliminates all identified BOLA/IDOR vulnerabilities (F-03, F-04, F-05, F-17).
  - Clear, declarative, and auditable access control logic.
- **Negative / Tradeoffs**:
  - Legacy routes must be refactored to query through the policy layer rather than directly querying raw IDs.
