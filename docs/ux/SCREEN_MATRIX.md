# SCREEN & VIEWPORT MATRIX (GOLDEN SCREENS)
**Target Breakpoints:**
1. Desktop Full (1440x900) — Clinician Workstation / Admin Command
2. Desktop Compact (1366x768) — Reception / Cashier Counter (Standard Indian Hospital Hardware)
3. Tablet (1024x768) — Ward Nurse Rounds / Mobile Clinician
4. Mobile (390x844) — Patient Self-Service Portal

---

## 1. Golden Screen Catalog

| Screen ID | Screen Name | Primary Role | Core Workflow | Viewport Verified | Key States Verified |
|---|---|---|---|---|---|
| **G1** | Hospital Operational Command | Admin | Real-time OPD queue volume, bed occupancy rate, revenue breakdown, unbilled encounters. | 1440x900, 1366x768 | Normal, Empty stats, Error fallback |
| **G2** | Reception OPD Command Board | Receptionist | Live queue tracking, token issue, patient fast-search, duplicate identity warning. | 1366x768 | Active queue, Empty queue, Duplicate match alert |
| **G3** | Clinician Encounter Workspace | Doctor | Assigned consultation list, patient longitudinal chart, vitals capture, structured Rx composition, note signing. | 1440x900, 1024x768 | Waiting patient, In-consultation, Signed note, Draft |
| **G4** | Patient Longitudinal Chart | Doctor / Admin | Historical visit timeline, allergies, past diagnoses, signed notes, admission history. | 1440x900, 1024x768 | Loaded history, First-time patient (Empty), Amended note view |
| **G5** | Appointment Scheduling Wizard | Receptionist / Patient | Conflict-free provider slot selection, department filter, calendar picker. | 1366x768, 390x844 | Available slots, Slot conflict error, Booking success |
| **G6** | Cashier Billing & Settle Ledger | Cashier | Itemized bill breakdown, verified payment capture (cash counter reference / draft), receipt generation. | 1366x768 | Unpaid, Cash settled, Demo simulation banner, Paid receipt |
| **G7** | Ward Bed-Board & IPD Roster | Admin / Doctor | Bed occupancy status cards, patient stay duration, atomic admission modal, unified discharge trigger. | 1440x900, 1024x768 | Full capacity, Available beds, Discharge confirmation |
| **G8** | Patient Portal | Patient | Personal appointment schedule, verified receipts, digital prescription summary. | 390x844 (Mobile) | Upcoming visits, Empty bills, Profile view |
| **G9** | Security & Audit Explorer | Admin | Immutable system audit log, filtering by user/action/date, session management. | 1440x900 | Loaded logs, Filtered view, Security alerts |
