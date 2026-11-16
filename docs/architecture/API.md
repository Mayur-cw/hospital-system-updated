# API & ROUTE CONTRACT SPECIFICATION — HOSPITAL OS
**Protocol:** HTTP/1.1 over TLS  
**Content Types:** `text/html` (Server-Rendered Jinja2 Views) and `application/json` (AJAX Endpoints)  
**Authentication:** Cookie Session with CSRF token (`X-CSRFToken` or `csrf_token` form field)  
**Error Standard:** RFC 7807 compatible JSON / User-friendly flashed notifications with correlation IDs

---

## 1. Authentication & Session API

### `POST /login`
- **Request (Form Data):** `email`, `password`, `csrf_token`
- **Response (302):** Redirect to validated relative `next` URL or role landing page.
- **Security Control:** Rate-limited; safe URL redirect validation; sets `HttpOnly`, `SameSite=Lax` cookie.

### `POST /logout`
- **Request (Form Data):** `csrf_token`
- **Response (302):** Redirect to `/login`. Session destroyed.
- **Security Control:** POST-only with CSRF to prevent pre-fetch or clickjacking logout.

---

## 2. Reception & OPD Scheduling API

### `GET /reception/queue`
- **Role:** Receptionist, Admin, Doctor
- **Query Params:** `date` (default today), `doctor_id` (optional filter)
- **Response:** HTML OPD Command Board with today's queue tokens and doctor availability.

### `POST /reception/register`
- **Role:** Receptionist, Admin
- **Request (Form Data):** `patient_name`, `phone`, `gender`, `dob`, `address`, `emergency_contact`, `csrf_token`
- **Response (302 / 200):** Creates new `Patient` with scoped MRN (`MRN-YYYY-NNNN`). If duplicate phone/name detected, displays match warning modal.

### `POST /patients` (Book Appointment)
- **Role:** Patient, Receptionist, Admin
- **Request (Form Data):** `doctor_id`, `date`, `time`, `disease`, `slot`, `csrf_token`
- **Response (302):**
  - Success: Redirect to `/booking_success/<apt_id>` with assigned token number.
  - Conflict (Slot taken): 302 back with flash `"Slot Unavailable: That time slot is already reserved. Please select another slot."`
- **Security Control:** Concurrency-safe atomic reservation; verifies patient ownership or staff privilege.

### `POST /reception/check_in/<int:apt_id>`
- **Role:** Receptionist, Admin
- **Request:** `csrf_token`
- **Response (302):** Transitions appointment state from `Scheduled` -> `CheckedIn`. Assigns live queue token.

---

## 3. Clinician Charting & EMR API

### `GET /add_record/<int:apt_id>`
- **Role:** Doctor (must be assigned to appointment) or Admin
- **Response:** Clinician Charting Workspace with patient longitudinal history, allergy banner, vitals, structured prescription form, and room admission option.

### `POST /add_record/<int:apt_id>`
- **Role:** Assigned Doctor
- **Request (Form Data):**
  - `diagnosis` (string, required)
  - `prescription_items` (JSON or structured rows: drug, dose, route, frequency, duration)
  - `notes` (string, optional)
  - `action` (`draft` | `sign`)
  - `room_id` (optional admission)
  - `csrf_token`
- **Response (302):** Saves draft or signs immutable clinical record. If admitted, allocates room atomically. Generates OPD invoice if outpatient.

### `POST /edit_record/<int:apt_id>`
- **Role:** Assigned Doctor
- **Request (Form Data):** `amendment_reason` (required), updated diagnosis/prescription fields, `csrf_token`.
- **Response (302):** Preserves original note in revision ledger; appends new amendment record with doctor ID and timestamp.

---

## 4. Inpatient & Ward Operations API

### `GET /admin/rooms` / `GET /doctor/my_admissions`
- **Role:** Admin, Doctor
- **Response:** Ward Bed-Board showing room number, ward type, occupancy status, admitted patient MRN, and length of stay.

### `POST /doctor/discharge_patient` / `POST /admin/discharge`
- **Role:** Assigned Doctor or Admin
- **Request (Form Data):** `admission_id`, `discharge_summary`, `csrf_token`
- **Response (302):** Unified Domain Discharge Service:
  1. Validates admission is currently `Admitted` (idempotent).
  2. Sets `discharge_date = NOW()`, `status = 'Discharged'`.
  3. Computes length of stay with tariff rules (`Decimal`).
  4. Generates single finalized `Billing` invoice.
  5. Transitions bed status to `Cleaning` (not immediately available until sanitized).

---

## 5. Billing, Cashier & Financial API

### `GET /bills/<int:bill_id>/invoice`
- **Role:** Patient (own bill), Cashier, Admin
- **Response:** Itemized medical invoice breakdown with GST, room charges, and consultation fee.

### `POST /cashier/settle/<int:bill_id>`
- **Role:** Cashier, Admin
- **Request (Form Data):** `payment_method` (`cash` | `upi` | `card` | `bank_transfer`), `cash_drawer_id`, `reference_no`, `csrf_token`
- **Response (302):** Records verified settlement, marks invoice `Paid`, sets `paid_on = NOW()`, and redirects to `/bills/<id>/receipt`.

### `POST /bills/<int:bill_id>/pay` (Patient Demo Simulation)
- **Role:** Patient (own bill)
- **Response (302):** In `DEMO_ONLY` mode, records simulated demo payment with explicit banner `DEMO_SIMULATION` on receipt. In production mode, rejects with `403 Forbidden` pending gateway activation.
