# ADR 0004: Strict Decimal Arithmetic for Financial Integrity (D-04)

## Status
Accepted

## Context
Financial calculations in healthcare billing must never exhibit binary floating-point rounding errors (e.g. `0.1 + 0.2 = 0.30000000000000004`). The previous code used Python `float` and SQL `FLOAT`/`DOUBLE` columns.

## Decision
We enforced Python's `decimal.Decimal` end-to-end:
- All database columns storing money (`Invoice.subtotal`, `Invoice.tax`, `Invoice.discount`, `Invoice.total`, `InvoiceItem.unit_price`, `Payment.amount`, `Room.rate_per_day`, `Doctor.consultation_fee`) use `db.Numeric(10, 2)`.
- All Python service calculations use `Decimal`. Floating-point conversion is strictly prohibited in models and billing services.
- Invoice totals are computed from discrete line items (`InvoiceItem`), never arbitrarily assigned by client requests.

## Consequences
- 100% financial audit compliance.
- Verified in characterization test `test_phase3_money_and_invoices_decimal`.
