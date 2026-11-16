# PRODUCT REQUIREMENTS DOCUMENT (PRD) — HOSPITAL OS
**Target Market:** Small to Midsize Indian Hospitals & OPD Clinics (10–50 beds, 50–300 daily OPD consultations)  
**Product Tier:** Commercial HIS Wedge — Outpatient Operations, Clinical Charting, and Inpatient Ward Management  
**Compliance / Governance Horizon:** India DPDP Act 2023 / Rules 2025 readiness, ABDM M1/M2 architectural compatibility, OWASP ASVS 5.0.0 Level 1/2 controls  
**Deployment Grade:** Transitioning from `DEV_ONLY` to `DEMO_READY` (Synthetic only; no live clinical deployment until external audit gates pass)

---

## 1. Problem Statement & Operational Context
Small and midsize hospitals in India frequently operate on fragile spreadsheet-driven or generic DBMS student projects that lack:
1. Guaranteed schedule concurrency (double-booking doctors during OPD peak hours).
2. Clinical chart immutability (doctors silently editing or deleting previous notes without audit).
3. Patient identification safety (missing MRN deduplication leading to mixed-up patient charts).
4. Financial truth (marking bills "Paid" without actual cashier cash drawer reconciliation or verified gateway callbacks).
5. Inpatient bed occupancy guarantees (double-allocating beds or discharging without billing).

Hospital OS solves these core operational bottlenecks with an operations-first, audit-grade, role-native platform.

---

## 2. Target User Personas & Workflows

### Persona A: Front-Desk Receptionist (Sunita)
- **Pain Point:** OPD morning rush, patients without appointments, duplicate registrations for same patient.
- **Workflow:** Fast keyboard-friendly patient search (by Mobile/Name/MRN) -> duplicate detection alert -> create visit/token -> assign available slot/doctor -> print OPD slip -> queue status update.

### Persona B: Consulting Doctor (Dr. Rajesh Sharma)
- **Pain Point:** Cluttered interfaces, losing notes midway, fear of medico-legal liability from overwritten charts.
- **Workflow:** OPD queue view -> 1-click patient chart access -> review history/allergies -> enter vitals -> structured diagnosis (ICD-ready) & medication prescription (drug, dose, frequency, duration) -> Sign Note (immutable) -> order admission if needed -> Complete consultation.

### Persona C: Hospital Cashier / Billing Executive (Vikram)
- **Pain Point:** Discrepancies between doctor discharge and cashier counter; fake "online payments" presented by patients.
- **Workflow:** Search patient/bill ID -> inspect itemized charges (consultation fee, bed charges, services) -> record verified payment mode (Cash with drawer reference, Netbanking/UPI with external UTR verification, or Approved Insurance) -> print official GST-compliant receipt -> shift daily close.

### Persona D: Hospital Administrator / Medical Superintendent (Dr. Mehta)
- **Pain Point:** Lack of visibility into bed occupancy, revenue leakage, unbilled patient discharges, unauthorized staff actions.
- **Workflow:** Live command dashboard (active queue, bed occupancy, collected vs pending revenue) -> staff provisioning & access revocation -> tariff master maintenance -> immutable audit log inspection.

### Persona E: Patient (Aarav)
- **Pain Point:** Long waiting lines, lost paper prescriptions, unverified billing.
- **Workflow:** View personal appointments, inspect visit summaries and signed prescriptions, view verified receipts, download discharge summary.

---

## 3. Core Functional Requirements & State Machines

### 3.1 Patient Identity & Deduplication
- **REQ-ID-01**: Patient entity is strictly decoupled from system login accounts.
- **REQ-ID-02**: Unique, deterministic Medical Record Number (MRN) generated per patient (e.g. `MRN-YYYY-NNNN`).
- **REQ-ID-03**: Registration algorithm checks phone number and full name; presents a duplicate-merge warning if potential match is detected.

### 3.2 Appointment Scheduling & OPD Queue
- **REQ-SCH-01**: Strict conflict prevention: No two active appointments for the same doctor at the same slot. Enforced via database unique constraint and transactional row lock.
- **REQ-SCH-02**: Appointment State Machine:
  `DRAFT -> SCHEDULED -> CHECKED_IN -> IN_CONSULTATION -> COMPLETED`  
  `Branches: CANCELLED, NO_SHOW`
- **REQ-SCH-03**: Live OPD queue tracks tokens with clear visual status tags (Waiting, With Doctor, Attended/Pending Rx, Completed, Missed).

### 3.3 Clinical Charting & Medication Safety
- **REQ-CLN-01**: Clinical Note Lifecycle: `DRAFT -> SIGNED -> AMENDED`.
- **REQ-CLN-02**: Once a note is signed by the attending clinician, it is permanently immutable. Any update requires an explicit amendment reason, preserving original text, author, and timestamp.
- **REQ-CLN-03**: Structured Prescriptions: Drug name, formulation (tablet/syrup/injection), strength, dosage, route, frequency, and duration.
- **REQ-CLN-04**: Patient Allergies & Vitals: Persistent visibility banner on the chart.

### 3.4 Inpatient Bed & Ward Management
- **REQ-IPD-01**: Ward -> Room -> Bed hierarchy. Each bed has status (`Available`, `Occupied`, `Cleaning`, `Maintenance`).
- **REQ-IPD-02**: Atomic Bed Allocation: Concurrency-safe admission. A bed cannot have two concurrent active occupants.
- **REQ-IPD-03**: Unified Discharge Service: Both Doctor and Admin discharge invoke the identical domain service, generating exactly one final itemized bill and transitioning the bed to `Cleaning` state.

### 3.5 Revenue Cycle & Financial Truth
- **REQ-FIN-01**: Fixed-point Decimal precision for all monetary values.
- **REQ-FIN-02**: Status `Paid` is ONLY set upon verified cashier settlement or signed provider webhook. Browser-declared payment is explicitly blocked and tagged as demo mock.
- **REQ-FIN-03**: Finalized invoices cannot be deleted; cancellations or adjustments require an audited adjustment ledger.

---

## 4. Non-Functional Requirements
- **NFR-SEC-01**: Zero hardcoded secrets; mandatory CSRF on all mutating routes; secure session cookies (HttpOnly, SameSite=Lax).
- **NFR-SEC-02**: Complete RBAC and object-level permission enforcement across all endpoints.
- **NFR-PERF-01**: Reception and Doctor dashboard queries paginated and indexed; P95 page load < 500ms on local LAN.
- **NFR-A11Y-01**: WCAG 2.2 AA compliant contrast, full keyboard navigation support, high-contrast operational theme.
