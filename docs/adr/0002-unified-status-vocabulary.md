# ADR 0002: Single Source of Truth for Status Vocabulary (D-02)

## Status
Accepted

## Context
Status terms were fragmented across the legacy codebase: appointments used "Pending", "Approved", "Attended", "Cancelled", while UI templates checked "Visited" or "Done". This caused broken UI state badges and discrepancies between doctor and patient views.

## Decision
We established a canonical status vocabulary governed by model constants and enums:
- `AppointmentStatus`: `Scheduled`, `CheckedIn`, `Completed`, `Cancelled`, `Missed`.
- `InvoiceStatus`: `Draft`, `Issued`, `Paid`, `Void`, `Refunded`.
- `PaymentStatus`: `Pending`, `Success`, `Failed`, `Refunded`.
- `RoomStatus`: `Available`, `Occupied`, `Maintenance`.
- `AdmissionStatus`: `Admitted`, `Discharged`.

A shared UI macro (`macros/components.html:status_badge`) maps every canonical state to standard semantic colors and accessible text.

## Consequences
- State transitions are strictly validated in `AppointmentStateMachine` and domain services.
- Invalid state transitions raise `InvalidStateTransitionError` returning HTTP 409 Conflict.
