# ADR 0006: Inpatient Clinical Admission Lifecycle & 24-Hour Block Billing (D-06)

## Status
Accepted

## Context
Inpatient bed management previously had discrepancies: beds were marked available before discharge clearance, and room rent calculations were inconsistent.

## Decision
We implemented a two-phase medical and administrative discharge lifecycle:
1. **Medical Clearance:** The attending doctor approves discharge (`approve_discharge`). The admission enters pending discharge state.
2. **Room Rent Generation:** Automated generation of the itemized room rent invoice based on started 24-hour blocks:
   $$\text{days} = \max\left(1, \left\lceil \frac{\text{seconds}}{86400} \right\rceil\right)$$
3. **Settlement & Bed Release:** Once the patient or insurance settles the generated invoice, the cashier confirms payment, the admission transitions to `Discharged`, and the room status transitions back to `Available`.
4. **Maintenance State:** Rooms can be placed in `Maintenance` mode for sanitization between occupancies.

## Consequences
- Prevents premature room double-allocation while patients are settling fees.
- Concurrency drill proves that simultaneous discharge requests yield exactly 1 generated invoice.
