# ADR-0004: Financial Truth and Payment Integrity
**Date:** 2026-11-17  
**Status:** ACCEPTED  
**Deciders:** Staff Engineer, Product Owner, QA Lead

## Context
In the original repository (`PROJECT/routes/patient.py:227-253`), submitting the payment form directly executes:
```python
invoice.status = 'Paid'
invoice.paid_on = db.func.now()
invoice.payment_mode = payment_mode
db.session.commit()
```
The client UI displayed a spinner stating "Establishing secure connection to your bank..." and "SSL Secured Transaction", giving the impression of an integrated payment gateway. In reality, any HTTP POST to `/bills/<id>/pay` instantly marked an invoice as paid with zero bank verification, signature validation, or settlement confirmation.

Additionally:
- Admin discharge (`admin.py:543`) discharged patients without generating an invoice, whereas doctor discharge (`doctor.py:118`) generated an invoice using floating-point math (`days * float(rate_per_day)`).
- Multiple discharge button clicks generated duplicate invoices.

## Decision
1. **Truth in Payment Handling**:
   - In development/demo environments, display an explicit, unmissable banner:
     `"DEMO SIMULATION — NO REAL FUNDS EXCHANGED — NOT AN APPROVED PAYMENT GATEWAY"`.
   - Never claim bank integration where none exists.
2. **Authorized Settlement Workflow**:
   - Legitimate status transitions from `Unpaid` to `Paid` require:
     a) **Cashier Recorded Settlement**: A Cashier/Admin records settlement with cash drawer session ID, receipt number, and payment instrument reference.
     b) **Verified Provider Webhook (Future Phase)**: Cryptographic signature verification, order matching, and idempotency checks before state update.
3. **Unified Domain Discharge Service**:
   - Consolidate all discharge actions (Admin and Doctor) into a single domain service: `InpatientService.discharge_patient(admission_id, actor)`.
   - Guaranteed idempotency: if already discharged, returns existing finalized bill without creating duplicates.
   - Exact decimal calculations using `Decimal` / integer paise to eliminate floating-point rounding errors.

## Consequences
- **Positive**:
  - Truthful financial state and compliance with medical-legal standards.
  - Eliminates duplicate billing and inconsistent discharge states (F-06, F-07, F-19).
- **Negative / Tradeoffs**:
  - Requires updating the patient bill UI to distinguish between cash counter settlement and online simulation.
