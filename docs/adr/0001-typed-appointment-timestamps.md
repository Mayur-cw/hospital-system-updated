# ADR 0001: Typed DateTime Timestamps for Appointments (D-01)

## Status
Accepted

## Context
The legacy application stored appointment scheduling information in separate loose `date` (string) and `time` (string) fields. This caused timezone ambiguities, invalid date parsing crashes during route rendering, and prevented performant chronological range indexing.

## Decision
We unified appointment scheduling into a single `starts_at` column of type `DATETIME` with an associated `duration_min` integer column (defaulting to 30 minutes). Timezone awareness is enforced with UTC storage in MySQL and formatted locally for display.

## Consequences
- Enables standard SQL range queries (`starts_at BETWEEN :start AND :end`).
- Eliminates brittle string parsing (`strptime`) in presentation templates.
- Backed by composite indexes `(doctor_id, starts_at)` and `(patient_id, starts_at)`.
