# SYSTEM COMPONENTS ARCHITECTURE — HOSPITAL OS
**Architectural Style:** Evolutionary Modular Monolith  
**Core Framework:** Python 3.9+ / Flask 2.3+ / SQLAlchemy 1.4+ / Flask-Login / Flask-WTF  
**Database Engines:** SQLite (Local Dev / In-Memory Unit & Integration Tests), MySQL 8+ / PostgreSQL 15+ (Staging / Production)

---

## 1. Modular Monolith Component Architecture

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT TIER                                       |
|  Desktop Reception / Clinician Workstation / Cashier Terminal / Patient Portal    |
|  HTML5 + Jinja2 + Bootstrap 5 + Clinical Precision Token CSS                      |
+------------------------------------------+----------------------------------------+
                                           | HTTP / HTTPS (Session Cookie + CSRF)
                                           v
+-----------------------------------------------------------------------------------+
|                            APPLICATION LAYER (FLASK)                              |
|                                                                                   |
|  [Security & Middleware]                                                          |
|  - CSRF Token Validation (Flask-WTF)                                              |
|  - Safe Redirect Validator (Open Redirect Prevention)                            |
|  - Security Headers (HSTS, CSP, X-Frame-Options, X-Content-Type)                  |
|  - Correlation ID & Audit Context Injection                                      |
|                                                                                   |
|  [Modular Blueprint Controllers]                                                  |
|  +--------------------+  +--------------------+  +--------------------+           |
|  |   auth_bp          |  |   main_bp          |  |   patient_bp       |           |
|  |   (Auth & Profile) |  |   (Dashboards)     |  |   (Book & Bills)   |           |
|  +--------------------+  +--------------------+  +--------------------+           |
|  +--------------------+  +--------------------+  +--------------------+           |
|  |   doctor_bp        |  |   admin_bp         |  |   reception_bp     |           |
|  |   (EMR & Charting) |  |   (Admin & Staff)  |  |   (Queue & Checkin)|           |
|  +--------------------+  +--------------------+  +--------------------+           |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                         CENTRAL AUTHORIZATION POLICY                              |
|  - @require_roles(*roles)                                                         |
|  - Object-Level Care-Relationship Policies:                                       |
|    can_access_appointment(), can_modify_appointment(), can_chart_encounter(),     |
|    can_access_invoice(), can_discharge_admission()                                |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                             DOMAIN SERVICE LAYER                                  |
|                                                                                   |
|  [IdentityService]        [SchedulingService]          [ClinicalService]          |
|  - MRN generation         - Atomic slot booking        - Note draft/sign/amend    |
|  - Duplicate detection    - Queue token allocation     - Structured prescriptions |
|  - Scoped role membership - State transitions          - Vitals & allergies       |
|                                                                                   |
|  [InpatientService]       [BillingService]             [AuditService]             |
|  - Atomic bed assignment  - Unified discharge invoice  - Immutable action ledger  |
|  - Bed state tracking     - Itemized tariff catalog    - Security event recording |
|  - Unified discharge      - Verified settlement        - PHI access logs          |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                         DATA ACCESS & PERSISTENCE LAYER                           |
|  - SQLAlchemy 1.4 ORM Repositories                                                |
|  - Transactional Isolation (`with_for_update()`)                                  |
|  - Invariant Constraints:                                                         |
|    * UNIQUE(doctor_id, date, time) active slots                                   |
|    * UNIQUE(room_id/bed_id) active admissions                                     |
|    * Non-destructive soft cancellations (no ON DELETE CASCADE)                    |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                                 DATABASE TIER                                     |
|  Dev / Testing: SQLite instance/hms_dev.db                                        |
|  Staging / Production: MySQL 8.0+ / PostgreSQL 15+                                |
+-----------------------------------------------------------------------------------+
```

---

## 2. Component Responsibility Matrix

| Component | Modules | Key Responsibilities | Primary Dependencies |
|---|---|---|---|
| **Core Security** | `config.py`, `security.py` | Strict env validation, fail-closed production config, CSRF enforcement, safe redirect resolution, password hashing. | Werkzeug, Flask-WTF |
| **Authorization Engine** | `authorization.py` | Centralized RBAC and object-level care-team access control. Prevents BOLA/IDOR vulnerabilities. | Flask-Login, ORM Models |
| **Scheduling Engine** | `services/scheduling.py` | Concurrency-safe slot reservation, OPD queue token management, doctor availability check. | DB Connection / Row Locks |
| **Clinical EMR Engine** | `services/clinical.py` | Encounter lifecycle, structured prescriptions, signed clinical note immutability and amendment versioning. | Identity, Scheduling |
| **Inpatient Engine** | `services/inpatient.py` | Ward/bed allocation, atomic occupancy guarantees, bed cleaning transitions, unified discharge execution. | Billing, Clinical |
| **Billing & Revenue** | `services/billing.py` | Itemized charges, room tariff daily calculation, cashier cash drawer settlement, simulated demo payment guard. | Inpatient, Scheduling |
| **Audit & Governance** | `services/audit.py` | Immutable security and operational event logging; tracking who accessed or modified patient data. | Core Security |
