# Hospital Management System — Billing Policy & Rules

## 1. Overview
All financial transactions within Hedgewar Hospital Management System are handled with strict mathematical precision using `Decimal` (mapped to `DECIMAL(10, 2)` in MySQL). Floating-point arithmetic is strictly prohibited.

## 2. Inpatient Room-Day Billing Rule (B-07)
### Policy
Hospital admissions are billed by **started 24-hour blocks** with a minimum charge of 1 full day (24 hours):
- **Formula:**
  $$\text{billed\_days} = \max\left(1, \left\lceil \frac{\text{stay\_duration\_in\_seconds}}{86400} \right\rceil\right)$$
- **Examples:**
  - Stay of 2 hours: $\lceil 2 / 24 \rceil = 1$ day.
  - Stay of 24 hours: $\lceil 24 / 24 \rceil = 1$ day.
  - Stay of 24 hours 1 minute: $\lceil 24.016 / 24 \rceil = 2$ days.
  - Stay of 47 hours: $\lceil 47 / 24 \rceil = 2$ days.
  - Stay of 49 hours: $\lceil 49 / 24 \rceil = 3$ days.

### Daily Rates by Ward Type
- **General Ward:** ₹1,000.00 / day
- **Maternity Ward:** ₹1,800.00 / day
- **VIP Suite:** ₹3,500.00 / day
- **ICU (Intensive Care Unit):** ₹5,000.00 / day

## 3. Outpatient Consultation Fees
- Doctor consultation fees are dynamically read from the attending physician's profile (`Doctor.consultation_fee`) or the department schedule, rather than hard-coded constants.
- Default baseline consultation: ₹500.00.

## 4. Payment Integrity & Idempotency (B-18, F-06)
- Cash payments must be recorded by authorized hospital cashier / admin staff.
- Self-checkout online payments (UPI, Card, NetBanking, Mock) generate a unique `idempotency_key` (`PAY-{invoice_id}-{hash}`) to prevent duplicate debit on network retries or double-clicking.
- An itemized `InvoiceItem` record is created for every line item (room rent, doctor consultation, pharmacy).
