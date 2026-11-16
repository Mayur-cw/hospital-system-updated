# LOCAL DEV SERVER STATUS & OPERATIONAL LOG
**Status:** ACTIVE & HEALTHY  
**Local Preview URL:** `http://127.0.0.1:5001/`  
**Health Check Endpoint:** `http://127.0.0.1:5001/health`  
**Host & Port:** `127.0.0.1:5001` (Port 5000 in use by system service; dynamically routed to 5001)  
**Process ID / Task:** Background Daemon Task `task-578` (Port 5001)  
**Python Runtime:** `.venv/bin/python` (Python 3.9.6)  
**Database:** SQLite `instance/hms_dev.db` (Normalized 3NF schema, initialized with safe synthetic dataset)  
**Security Mode:** `DEMO_ONLY=True`, `FLASK_DEBUG=False`, `WTF_CSRF_ENABLED=True`

---

## 1. Verified Live Health Check Output
```json
{
  "database": "healthy",
  "environment": "development",
  "mode": "DEMO_ONLY",
  "status": "UP",
  "timestamp": "2026-11-16T19:18:07.325625"
}
```

---

## 2. Server Start & Recovery Command
If the server process ever terminates or requires a restart, execute:
```bash
PORT=5001 .venv/bin/python PROJECT/app.py
```
Or to run with full hot-reloading in isolated development:
```bash
FLASK_DEBUG=false PORT=5001 .venv/bin/python PROJECT/app.py
```

---

## 3. Seeded Synthetic Demo Credentials (Non-Production Only)
| Role | Email | Password | Display Name & Department / Notes |
|---|---|---|---|
| **Administrator** | `admin@hospital.local` | `AdminPass@2026` | Dr. Amit Mehta (Medical Superintendent) |
| **Doctor (Cardiology)** | `dr.sharma@hospital.local` | `DoctorPass@2026` | Dr. Rajesh Sharma (Cardiology) |
| **Doctor (Dermatology)** | `dr.patel@hospital.local` | `DoctorPass@2026` | Dr. Ananya Patel (Dermatology) |
| **Doctor (Infectious Disease)** | `dr.verma@hospital.local` | `DoctorPass@2026` | Dr. Vikram Verma (Infectious Disease) |
| **Receptionist** | `receptionist@hospital.local` | `StaffPass@2026` | Sunita Frontdesk (OPD Desk) |
| **Cashier / Billing** | `cashier@hospital.local` | `StaffPass@2026` | Vikram Cashier (Revenue Office) |
| **Patient 1** | `patient1@hospital.local` | `PatientPass@2026` | Aarav Mehta (MRN-2026-0001, Penicillin Allergy) |
| **Patient 2** | `patient2@hospital.local` | `PatientPass@2026` | Pooja Nair (MRN-2026-0002) |
| **Patient 3** | `patient3@hospital.local` | `PatientPass@2026` | Sunil Deshmukh (MRN-2026-0003, Admitted in ICU 201) |
