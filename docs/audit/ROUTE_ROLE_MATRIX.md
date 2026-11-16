# ROUTE & ROLE AUTHORIZATION MATRIX — HOSPITAL OS
**Audit Date:** 2026-11-17  
**Scope:** Complete inventory of all existing HTTP endpoints, current role enforcement, verified defects, and target hardened access rules.

---

## 1. Role Definitions & Access Principles
- **Admin**: System administration, staff provisioning, master facility settings, room management, high-level operational overview. NO unauthorized medical chart editing.
- **Doctor / Clinician**: Management of assigned consultations, clinical chart drafting, signing and amending, assigned inpatient care, clinical discharge authorization.
- **Receptionist (NEW OPD ROLE)**: Patient registration, identity deduplication, appointment scheduling, queue check-in, token generation. Minimal PHI view.
- **Billing / Cashier (NEW REVENUE ROLE)**: Invoice inspection, verified payment recording (cash / card / bank draft / verified gateway), receipt generation, shift reconciliation. No clinical data alteration.
- **Patient**: Viewing personal appointments, viewing personal invoices and receipts, booking requests, profile updates. Strictly isolated to own records.
- **Anonymous / Public**: Index view, doctor directory, login, patient registration (if self-service).

---

## 2. Comprehensive Endpoint Audit Matrix

| Blueprint | Method | Route | Login Req | Current Allowed Roles | Object-Level Check? | Verified Vulnerability / Defect | Hardened Target Rule |
|---|---|---|---|---|---|---|---|
| `main` | `GET` | `/` | Optional | All / Anonymous | N/A | None (role dispatch), but doctor view does unbounded memory loading (`MedicalRecord.query.all()`). | Keep role dispatch; scope doctor queue queries by `doctor_id` and indexed count. |
| `main` | `GET` | `/doctors` | No | Public | N/A | Exposes doctor emails publicly. | Keep public directory with sanitized practitioner information (name, department, OPD timings). |
| `auth` | `GET, POST` | `/login` | No | Anonymous | N/A | **F-11**: Unvalidated `next` parameter permits open external redirect. **F-13**: No CSRF on POST. | Validate `next` against safe relative URLs only; add CSRF token; rate-limit login attempts. |
| `auth` | `GET, POST` | `/signup` | No | Anonymous | N/A | **F-13**: No CSRF on POST. Hardcoded `usertype = "Patient"`. | Add CSRF token; input validation for name, phone, email, password strength. |
| `auth` | `GET` | `/logout` | Yes | Any authenticated | N/A | **F-12**: State mutation via HTTP GET. Vulnerable to link prefetch and CSRF. | Change to `POST /logout` with mandatory CSRF token verification. |
| `auth` | `GET, POST` | `/profile` | Yes | Any authenticated | Self | **F-13**: No CSRF on POST. Doctor email update previously desynchronized. | Enforce CSRF; separate user profile from patient clinical demographics. |
| `patient` | `POST` | `/get_booked_slots` | Yes | Any authenticated | None | Denormalized query on string `doctor` name. | Validate provider ID and fetch slots via schedule domain service. |
| `patient` | `GET, POST` | `/patients` | Yes | Any authenticated | None | **F-16**: Any user can book; relies on MySQL procedure `CALL BookAppointmentSafe`. No DB unique key. | Enforce Patient or Receptionist role; transactional booking with DB unique constraint on `(practitioner_id, date, time)`. |
| `patient` | `GET` | `/booking_success/<int:apt_id>` | Yes | Patient, Doctor | Flawed | **F-17**: Any doctor can view any patient's booking confirmation page (`usertype != "Doctor" and appointment.user_id != current_user.id`). | Allow only owning patient, assigned doctor, or reception staff. |
| `patient` | `GET` | `/dashboard` | Yes | Patient, Doctor | Owner / Doctor name | Role-overloaded route displaying either patient history or doctor schedule. | Separate Reception/Patient/Doctor dashboards cleanly. |
| `patient` | `GET` | `/upcoming_bookings` | Yes | Patient, Doctor | Owner / Doctor name | Overloaded route filtering future dates in Python memory. | Standardized query filtering in database. |
| `patient` | `GET` | `/past_records` | Yes | Patient, Doctor | Owner / Doctor name | Overloaded route filtering past records in Python memory. | Scoped pagination via database repository. |
| `patient` | `GET` | `/my_bills` | Yes | Patient | Owner | Only Patient allowed; redirects others to index without clear message. | Standardized authorization denial and pagination. |
| `patient` | `GET` | `/bills/<int:bill_id>/invoice` | Yes | Patient | Yes (`user_id == current_user.id`) | Properly checks ownership, but redirects to receipt if already paid. | Preserve ownership check; add Cashier/Admin access. |
| `patient` | `POST` | `/bills/<int:bill_id>/pay` | Yes | Patient | Yes (`user_id == current_user.id`) | **F-06**: Marks invoice `Paid` immediately on POST of simulated payment mode. False settlement! **F-13**: No CSRF. | Block simulated payment from creating real 'Paid' record; require Cashier settlement or signed gateway webhook. |
| `patient` | `GET` | `/bills/<int:bill_id>/receipt` | Yes | Any authenticated | Partial | Patient checks ownership; other roles bypass check. | Allow only owning patient, attending doctor, cashier, or admin. |
| `doctor` | `POST` | `/cancel_apt/<int:apt_id>` | Yes | Patient, Doctor | Name check | Compares doctor name by lowercase string matching (`appointment.doctor.lower()`). | Check foreign key `doctor.user_id == current_user.id`. |
| `doctor` | `POST` | `/mark_missed/<int:apt_id>` | Yes | Doctor | **None (F-03)** | Any logged-in Doctor can mark ANY appointment as Missed. BOLA/IDOR. | Enforce that `appointment.doctor_id == current_doctor.did`. |
| `doctor` | `POST` | `/mark_attended/<int:apt_id>` | Yes | Doctor | **None (F-03)** | Any logged-in Doctor can mark ANY appointment as Attended. BOLA/IDOR. | Enforce that `appointment.doctor_id == current_doctor.did`. |
| `doctor` | `GET, POST` | `/add_record/<int:apt_id>` | Yes | Doctor | **None (F-04)** | Any logged-in Doctor can chart notes for ANY appointment. **F-22**: Free-text prescription. | Enforce assigned provider check; structured prescriptions; note draft/sign workflow. |
| `doctor` | `GET` | `/my_admissions` | Yes | Doctor | Doctor ID | Correctly scopes admissions by `doctor_id = doc_profile.did`. | Keep and expand to show bed status and transfer state. |
| `doctor` | `POST` | `/discharge_patient` | Yes | Doctor | **None (F-05)** | Any doctor can discharge any admission; no check if already discharged; generates bill. | Idempotent domain discharge service; ownership check; unified billing calculation. |
| `doctor` | `GET` | `/view_record/<int:apt_id>` | Yes | Patient, Doctor | Partial | Doctor check compares username string. | Enforce foreign key relationship or care-team grant. |
| `doctor` | `GET, POST` | `/edit_record/<int:apt_id>` | Yes | Doctor | Name check | Silently overwrites clinical note without revision history or amendment audit. | Enforce immutable signed notes; require explicit amendment reason and append-only version. |
| `admin` | `GET` | `/admin/dashboard` | Yes | Admin | Admin role | Proper role check. | Add operational KPI metrics (queue length, occupancy, unbilled encounters). |
| `admin` | `GET` | `/admin/details` | Yes | Admin | Admin role | Audit log viewer. | Enhance with correlation IDs, IP/user agent, and filter by action type. |
| `admin` | `GET` | `/admin/staff` | Yes | Admin | Admin role | Staff listing. | Include role-based permission display and deactivation flags. |
| `admin` | `POST` | `/admin/add_staff` | Yes | Admin | Admin role | **F-13**: No CSRF. Sets user and doctor records. | Enforce CSRF; enforce password complexity; audit account creation. |
| `admin` | `POST` | `/admin/edit_staff` | Yes | Admin | Admin role | Updates staff details. | Enforce CSRF; audit modifications. |
| `admin` | `POST` | `/admin/change_staff_password` | Yes | Admin | Admin role | Updates staff password. | Enforce CSRF; enforce minimum password entropy. |
| `admin` | `POST` | `/admin/delete_staff` | Yes | Admin | Admin role | Hard deletes User. Breaks historical FK references if cascade occurs! | Soft-deactivate user account instead of hard delete. |
| `admin` | `GET` | `/admin/doctors` | Yes | Admin | Admin role | Doctor list. | Maintain and link to practitioner schedules. |
| `admin` | `POST` | `/admin/edit_doctor` | Yes | Admin | Admin role | Edit doctor details and department. | Enforce CSRF; audit changes. |
| `admin` | `POST` | `/admin/change_doctor_password` | Yes | Admin | Admin role | Change password. | Enforce CSRF; audit changes. |
| `admin` | `POST` | `/admin/delete_doctor` | Yes | Admin | Admin role | Hard deletes doctor and user. | Soft-deactivate doctor profile to preserve clinical note author attribution. |
| `admin` | `GET` | `/admin/patients` | Yes | Admin | Admin role | Patient list with basic search. | Add MRN search, pagination, and duplicate flag indicators. |
| `admin` | `GET` | `/admin/appointments` | Yes | Admin | Admin role | Appointment schedule view. | Add status filtering and queue state transitions. |
| `admin` | `POST` | `/admin/update_appointment_status` | Yes | Admin | Admin role | **F-18**: Open redirect via `redirect_url` form field. **F-13**: No CSRF. | Safe redirect validation; validate status transitions against appointment state machine. |
| `admin` | `POST` | `/admin/delete_appointment` | Yes | Admin | Admin role | **F-09**: Hard deletion of appointment record. Destroys audit and history. | Disallow physical delete; transition status to `Cancelled` or `Voided` with recorded reason. |
| `admin` | `GET` | `/admin/financials` | Yes | Admin | Admin role | Revenue summary and bill list. | Add payment method breakdown and shift settlement reconciliation. |
| `admin` | `GET` | `/admin/financials/<int:bill_id>/invoice` | Yes | Admin | Admin role | Admin view of invoice. | Add print stylesheet and itemized service details. |
| `admin` | `GET` | `/admin/financials/<int:bill_id>/receipt` | Yes | Admin | Admin role | Admin view of receipt. | Add print stylesheet and audit trail. |
| `admin` | `GET` | `/admin/rooms` | Yes | Admin | Admin role | Room inventory and active admissions. | Expand to ward/room/bed hierarchy with bed cleaning and readiness states. |
| `admin` | `POST` | `/admin/add_room` | Yes | Admin | Admin role | Add room. | Enforce CSRF; validate numeric tariff. |
| `admin` | `POST` | `/admin/edit_room` | Yes | Admin | Admin role | Edit room number, ward, rate, status. | Enforce CSRF; prevent marking occupied room as available without discharge. |
| `admin` | `POST` | `/admin/delete_room` | Yes | Admin | Admin role | Delete room. | Disallow deletion of rooms with historical admissions; archive instead. |
| `admin` | `POST` | `/admin/discharge` | Yes | Admin | Admin role | **F-07**: Marks admission `Discharged` BUT DOES NOT CREATE FINAL BILL! | Route through unified Domain Discharge Service shared with Doctor discharge. |
