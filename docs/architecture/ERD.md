# ENTITY RELATIONSHIP DIAGRAM (ERD) — HOSPITAL OS
**Status:** Evolved Normal Form (3NF with Immutable Audit Ledgers)  
**Safety Invariant:** Forward-only additive evolution; zero destructive cascade deletes on clinical/financial tables.

---

## 1. Relational Schema Diagram (Mermaid)

```mermaid
erDiagram
    USER ||--o{ DOCTORS : "has doctor profile"
    USER ||--o{ APPOINTMENTS : "books / attended as patient"
    USER ||--o{ BILLING : "receives bill"
    USER ||--o{ ADMISSION : "admitted as patient"
    USER ||--o{ AUDIT_LOG : "triggers audit event"

    DOCTORS ||--o{ APPOINTMENTS : "consults on"
    DOCTORS ||--o{ ADMISSION : "attending physician"

    APPOINTMENTS ||--o{ MEDICAL_RECORD : "yields clinical note"
    APPOINTMENTS ||--o| BILLING : "generates invoice"
    APPOINTMENTS ||--o| ADMISSION : "leads to admission"

    MEDICAL_RECORD ||--o{ CLINICAL_NOTE_REVISION : "has amendment trail"
    MEDICAL_RECORD ||--o{ PRESCRIPTION_ITEM : "contains structured meds"

    ROOMS ||--o{ ADMISSION : "houses"
    
    BILLING ||--o{ PAYMENT_TRANSACTION : "settled by"
    BILLING ||--o{ BILL_ITEM : "itemized with"

    USER {
        int id PK
        string username
        string usertype "Admin | Doctor | Patient | Receptionist | Cashier"
        string email UK
        string password
        string phone
        string gender
        string mrn UK "Medical Record Number (Patient)"
        datetime date_of_birth
        boolean is_active
        datetime created_at
    }

    DOCTORS {
        int did PK
        int user_id FK
        string dept
        string consultation_fee
        string room_no
        boolean is_available
    }

    APPOINTMENTS {
        int apt_id PK
        int user_id FK "Patient"
        int doctor_id FK "Doctor did"
        string doctor "Legacy display name"
        string dept
        string slot "Scheduled | CheckedIn | InConsultation | Attended | Completed | Missed | Cancelled"
        string disease "Chief Complaint"
        string time "09:30 AM"
        date appointment_date
        string date "Legacy YYYY-MM-DD"
        int token_number
        datetime created_at
    }

    MEDICAL_RECORD {
        int record_id PK
        int apt_id FK
        int signed_by_doctor_id FK
        string diagnosis
        string prescription "Structured JSON / text"
        string notes
        string status "Draft | Signed | Amended"
        datetime signed_at
        datetime created_at
    }

    CLINICAL_NOTE_REVISION {
        int revision_id PK
        int record_id FK
        int author_doctor_id FK
        string previous_diagnosis
        string new_diagnosis
        string amendment_reason
        datetime amended_at
    }

    PRESCRIPTION_ITEM {
        int item_id PK
        int record_id FK
        string drug_name
        string dosage "500mg"
        string route "Oral"
        string frequency "TDS (3 times/day)"
        string duration "5 days"
        string instructions "After food"
    }

    ROOMS {
        int room_id PK
        string room_number UK
        string ward_type "General | ICU | VIP | Maternity"
        decimal rate_per_day
        string status "Available | Occupied | Cleaning | Maintenance"
    }

    ADMISSION {
        int admission_id PK
        int apt_id FK
        int patient_id FK
        int doctor_id FK
        int room_id FK
        datetime admission_date
        datetime discharge_date
        string status "Admitted | Billing Pending | Discharged"
        string discharge_summary
        int tentative_days
        boolean discharge_approved
        datetime discharge_approved_at
        string discharge_rejection_reason
        int actual_days
        string stay_extended_notes
        boolean discharge_requested
        datetime discharge_requested_at
        string discharge_notes
    }

    BILLING {
        int bill_id PK
        int apt_id FK
        int user_id FK
        decimal amount
        string status "Unpaid | Paid | Refunded | Cancelled"
        datetime issued_on
        datetime paid_on
        string payment_mode "cash | upi | card | netbanking | demo_simulation"
        string transaction_ref
        string cashier_notes
    }

    BILL_ITEM {
        int bill_item_id PK
        int bill_id FK
        string description
        int quantity
        decimal unit_price
        decimal total_price
    }

    AUDIT_LOG {
        int tid PK
        int apt_id
        int user_id
        string action
        string details
        string ip_address
        string timestamp
    }
```

---

## 2. Invariants & Integrity Constraints
1. **Appointment Uniqueness**:
   `CONSTRAINT uq_doctor_slot UNIQUE (doctor_id, appointment_date, time, status_active)`
   Prevents double-booking doctors for the same slot.
2. **Bed Occupancy Uniqueness**:
   Only one active record in `ADMISSION` with `status = 'Admitted'` per `room_id`.
3. **Clinical Immutability**:
   `MEDICAL_RECORD` rows with `status = 'Signed'` cannot be overwritten in place; updates insert an immutable record into `CLINICAL_NOTE_REVISION`.
4. **Permanent Financial Ledger**:
   `BILLING` records are never dropped or cascade deleted. Corrections require offsetting adjustment rows or status flags.
