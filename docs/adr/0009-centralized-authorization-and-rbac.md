# ADR 0009: Centralized Object-Level Authorization & RBAC Policies (D-09)

## Status
Accepted

## Context
Scattering role checks (`if current_user.usertype == 'Admin'`) across ad-hoc template files and route controllers leads to permission leaks, privilege escalation, and insecure direct object reference (IDOR) vulnerabilities.

## Decision
We centralized all authorization logic in `hms/policies.py`:
- Principle: **Deny by Default**.
- Route decorators: `@roles_required(*roles)`, `@admin_required`, `@doctor_required`, `@patient_required`. Unauthenticated requests redirect to login (or 401 for `/api/`), unauthorized requests raise HTTP 403 Forbidden.
- Fine-grained object policies:
  - `can_view_appointment(user, apt)`: Admins, attending doctor, booking patient.
  - `can_view_medical_record(user, rec)`: Admins, attending doctor, patient.
  - `can_edit_medical_record(user, rec)`: Only the treating doctor or administrator.
  - `can_view_invoice(user, inv)`: Admins, billing receptionists, patient.
  - `can_record_payment(user)`: Only admins and billing receptionists.

## Consequences
- Single location to inspect, audit, and test authorization policies.
- Validated by the automated URL map authorization matrix test (`tests/unit/test_authorization_matrix.py`).
