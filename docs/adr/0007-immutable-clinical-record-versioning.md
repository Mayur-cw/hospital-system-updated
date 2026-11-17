# ADR 0007: Versioned Medical Records & Clinical Non-Repudiation (D-07)

## Status
Accepted

## Context
In medical systems, clinical consultations, diagnoses, and prescriptions cannot be silently edited or overwritten in place without an audit trail, as this violates non-repudiation and clinical governance standards.

## Decision
We implemented a versioned clinical record architecture:
- `MedicalRecord`: Holds the active `is_latest` record with incremental `version` numbers.
- `MedicalRecordVersion`: Whenever a record is amended, the previous state is snapshot into an immutable `medical_record_versions` table recording `previous_diagnosis`, `previous_notes`, `amended_by`, `amended_at`, and the mandatory clinical amendment reason.
- `PrescriptionItem`: Discrete line items linking medication name, dose, frequency, duration, and instructions to the clinical consultation.

## Consequences
- Full clinical audit history is available to attending physicians.
- Transparent record amendments without data loss.
