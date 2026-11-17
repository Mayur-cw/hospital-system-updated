# ADR 0005: Soft Deletes and Strict Referential Safety (D-05)

## Status
Accepted

## Context
Hospital medical records, prescription histories, and financial ledgers must be retained for legal and regulatory compliance. Hard deletes and cascading deletes (`ON DELETE CASCADE`) introduce catastrophic risks of data loss.

## Decision
1. Implemented `SoftDeleteMixin` (`is_active: bool`, `deleted_at: DateTime`) on User, Doctor, Appointment, and Room.
2. Configured `ON DELETE RESTRICT` on all foreign key constraints linking clinical records, appointments, admissions, and financial invoices.
3. In the user interface, "delete" deactivates records by setting `is_active = False` and stamping `deleted_at`. Any user with existing appointment, clinical, or billing history cannot be hard deleted.

## Consequences
- Historical clinical data is permanently preserved.
- Database foreign key constraints prevent accidental orphaned or purged transactions.
