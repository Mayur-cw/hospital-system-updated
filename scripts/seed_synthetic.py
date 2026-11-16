import sys
import os
from pathlib import Path

# Add PROJECT directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'PROJECT'))

from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import create_app
from models import (
    db, User, Doctors, Appointments, MedicalRecord, 
    PrescriptionItem, ClinicalNoteRevision, Billing, Room, Admission, AuditLog
)

def seed_synthetic_data(force=False):
    app = create_app()
    with app.app_context():
        if force:
            print("Resetting and recreating clean database schema...")
            db.drop_all()
            db.create_all()
        else:
            db.create_all()
            if User.query.filter_by(email='admin@hospital.local').first():
                print("Synthetic data already present. Use force=True to reseed.")
                return

        print("Seeding comprehensive synthetic hospital dataset...")

        # -------------------------------------------------------------
        # 1. CORE STAFF ACCOUNTS (Admin & Doctors only; Receptionist removed)
        # -------------------------------------------------------------
        admin = User(
            id=1,
            username='Dr. Amit Mehta',
            usertype='Admin',
            email='admin@hospital.local',
            password=generate_password_hash('AdminPass@2026'),
            phone='555-0100',
            gender='Male'
        )
        db.session.add(admin)

        doc1_user = User(
            id=2,
            username='Dr. Rajesh Sharma',
            usertype='Doctor',
            email='dr.sharma@hospital.local',
            password=generate_password_hash('DoctorPass@2026'),
            phone='555-0101',
            gender='Male'
        )
        doc2_user = User(
            id=3,
            username='Dr. Ananya Patel',
            usertype='Doctor',
            email='dr.patel@hospital.local',
            password=generate_password_hash('DoctorPass@2026'),
            phone='555-0102',
            gender='Female'
        )
        doc3_user = User(
            id=4,
            username='Dr. Vikram Verma',
            usertype='Doctor',
            email='dr.verma@hospital.local',
            password=generate_password_hash('DoctorPass@2026'),
            phone='555-0103',
            gender='Male'
        )
        cashier_user = User(
            id=5,
            username='Vikram Cashier',
            usertype='Cashier',
            email='cashier@hospital.local',
            password=generate_password_hash('StaffPass@2026'),
            phone='555-0105',
            gender='Male'
        )
        db.session.add_all([doc1_user, doc2_user, doc3_user, cashier_user])
        db.session.flush()

        # Doctor Profiles & Departments
        doc1 = Doctors(did=1, user_id=doc1_user.id, dept='Cardiologists')
        doc2 = Doctors(did=2, user_id=doc2_user.id, dept='Dermatologists')
        doc3 = Doctors(did=3, user_id=doc3_user.id, dept='Infectious Disease')
        db.session.add_all([doc1, doc2, doc3])
        db.session.flush()

        # -------------------------------------------------------------
        # 2. PATIENT ACCOUNTS (Specific current demo IDs + cohort)
        # -------------------------------------------------------------
        p1 = User(
            id=6,
            username='Aarav Mehta',
            usertype='Patient',
            email='patient1@hospital.local',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0201',
            gender='Male',
            mrn='MRN-2026-0001',
            allergies='Penicillin allergy (severe urticaria)',
            blood_group='O+'
        )
        p2 = User(
            id=7,
            username='Pooja Nair',
            usertype='Patient',
            email='patient2@hospital.local',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0202',
            gender='Female',
            mrn='MRN-2026-0002',
            allergies='None known',
            blood_group='B+'
        )
        p3 = User(
            id=8,
            username='Sunil Deshmukh',
            usertype='Patient',
            email='patient3@hospital.local',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0203',
            gender='Male',
            mrn='MRN-2026-0003',
            allergies='NSAIDs (Aspirin induced bronchospasm)',
            blood_group='A+'
        )
        p4 = User(
            id=9,
            username='Mayur Wakchaure',
            usertype='Patient',
            email='mayur132005@gmail.com',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0204',
            gender='Male',
            mrn='MRN-2026-0004',
            allergies='Sulfa antibiotics',
            blood_group='B+'
        )
        p5 = User(
            id=10,
            username='Neha Sharma',
            usertype='Patient',
            email='patient5@hospital.local',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0205',
            gender='Female',
            mrn='MRN-2026-0005',
            allergies='Latex',
            blood_group='AB+'
        )
        p6 = User(
            id=11,
            username='Rohan Kulkarni',
            usertype='Patient',
            email='patient6@hospital.local',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0206',
            gender='Male',
            mrn='MRN-2026-0006',
            allergies='None known',
            blood_group='O-'
        )
        p7 = User(
            id=12,
            username='Kavita Iyer',
            usertype='Patient',
            email='patient7@hospital.local',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0207',
            gender='Female',
            mrn='MRN-2026-0007',
            allergies='Ciprofloxacin',
            blood_group='A-'
        )
        p8 = User(
            id=13,
            username='Vikramaditya Joshi',
            usertype='Patient',
            email='patient8@hospital.local',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0208',
            gender='Male',
            mrn='MRN-2026-0008',
            allergies='None known',
            blood_group='B-'
        )
        patients = [p1, p2, p3, p4, p5, p6, p7, p8]
        db.session.add_all(patients)
        db.session.flush()

        # -------------------------------------------------------------
        # 3. HOSPITAL ROOMS / INPATIENT CAPACITY
        # -------------------------------------------------------------
        r1 = Room(room_id=1, room_number='101', ward_type='General', rate_per_day=Decimal('800.00'), status='Available')
        r2 = Room(room_id=2, room_number='102', ward_type='General', rate_per_day=Decimal('800.00'), status='Available')
        r3 = Room(room_id=3, room_number='201', ward_type='ICU', rate_per_day=Decimal('3500.00'), status='Occupied')
        r4 = Room(room_id=4, room_number='301', ward_type='VIP', rate_per_day=Decimal('5000.00'), status='Occupied')
        db.session.add_all([r1, r2, r3, r4])
        db.session.flush()

        # -------------------------------------------------------------
        # 4. COMPREHENSIVE APPOINTMENTS DATASET
        # -------------------------------------------------------------
        today_date = date.today()
        today_str = today_date.isoformat()
        
        appointments_data = [
            # --- PAST COMPLETED CLINICAL VISITS (History) ---
            {
                "apt_id": 1, "user_id": p1.id, "slot": "Completed", "disease": "Hypertension & Exertional Chest Heaviness",
                "time": "10:00 AM", "date": (today_date - timedelta(days=6)).isoformat(),
                "dept": "Cardiologists", "doctor": "Dr. Rajesh Sharma", "token": 1,
                "diagnosis": "Essential Hypertension Stage II, Stable Angina",
                "prescription": "Telmisartan 40mg OD, Atorvastatin 20mg HS, Aspirin 75mg OD after breakfast",
                "notes": "BP: 154/96 mmHg. ECG shows mild LVH. Advised salt restriction and 2D-Echo.",
                "meds": [
                    ("Telmisartan", "40mg", "Oral", "1-0-0", "30 days", "Before food in morning"),
                    ("Atorvastatin", "20mg", "Oral", "0-0-1", "30 days", "At bedtime"),
                    ("Aspirin", "75mg", "Oral", "0-1-0", "30 days", "After lunch")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "upi"
            },
            {
                "apt_id": 2, "user_id": p2.id, "slot": "Completed", "disease": "Severe Eczematous Dermatitis",
                "time": "11:15 AM", "date": (today_date - timedelta(days=5)).isoformat(),
                "dept": "Dermatologists", "doctor": "Dr. Ananya Patel", "token": 2,
                "diagnosis": "Subacute Atopic Dermatitis, secondary bacterial impetiginization",
                "prescription": "Mometasone furoate 0.1% cream apply BD, Desloratadine 5mg OD, Mupirocin ointment local",
                "notes": "Severe erythema and excoriations over bilateral flexor surfaces. Advised emollient therapy.",
                "meds": [
                    ("Mometasone Cream 0.1%", "Topical", "Topical", "1-0-1", "10 days", "Apply thin layer to affected skin"),
                    ("Desloratadine", "5mg", "Oral", "0-0-1", "14 days", "At night"),
                    ("Mupirocin Ointment 2%", "Topical", "Topical", "1-0-1", "7 days", "Apply after cleaning")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "card"
            },
            {
                "apt_id": 3, "user_id": p3.id, "slot": "Completed", "disease": "Acute Febrile Illness & Bronchospasm",
                "time": "02:30 PM", "date": (today_date - timedelta(days=4)).isoformat(),
                "dept": "Infectious Disease", "doctor": "Dr. Vikram Verma", "token": 1,
                "diagnosis": "Acute Severe Bronchitis with Bronchospasm, High Grade Pyrexia",
                "prescription": "Admitted to ICU for monitored oxygenation and IV bronchodilator therapy.",
                "notes": "SpO2 91% on room air. Rhonchi in bilateral lower lobes. Admitted to ICU Bed 201.",
                "meds": [
                    ("Levofloxacin IV", "500mg", "IV", "0-1-0", "5 days", "Infuse over 60 mins"),
                    ("Hydrocortisone IV", "100mg", "IV", "1-0-1", "3 days", "IV bolus"),
                    ("Duolin Inhaler", "2 puffs", "Inhalation", "1-1-1", "7 days", "With spacer")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "cash"
            },
            {
                "apt_id": 4, "user_id": p4.id, "slot": "Completed", "disease": "Acid Reflux & Epigastric Burning",
                "time": "03:45 PM", "date": (today_date - timedelta(days=4)).isoformat(),
                "dept": "Infectious Disease", "doctor": "Dr. Vikram Verma", "token": 2,
                "diagnosis": "Gastroesophageal Reflux Disease (GERD) with Antral Gastritis",
                "prescription": "Pantoprazole 40mg OD before breakfast, Sucralfate suspension 10ml TDS",
                "notes": "Urea breath test negative for H. pylori. Advised dietary lifestyle modifications.",
                "meds": [
                    ("Pantoprazole", "40mg", "Oral", "1-0-0", "28 days", "30 mins before breakfast"),
                    ("Sucralfate Suspension", "10ml", "Oral", "1-1-1", "14 days", "1 hour before meals")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "upi"
            },
            {
                "apt_id": 5, "user_id": p5.id, "slot": "Completed", "disease": "Chronic Plaque Psoriasis",
                "time": "10:30 AM", "date": (today_date - timedelta(days=3)).isoformat(),
                "dept": "Dermatologists", "doctor": "Dr. Ananya Patel", "token": 1,
                "diagnosis": "Psoriasis Vulgaris, PASI Score 8.2",
                "prescription": "Calcipotriol + Betamethasone gel OD, Coal tar shampoo twice weekly",
                "notes": "Well-demarcated scaly plaques over extensor elbows and scalps. Improving on topical calcipotriol.",
                "meds": [
                    ("Calcipotriol Betamethasone Gel", "Topical", "Topical", "0-0-1", "30 days", "Apply at bedtime"),
                    ("Coal Tar Shampoo", "100ml", "Topical", "Twice/week", "4 weeks", "Leave on scalp 5 minutes")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "netbanking"
            },
            {
                "apt_id": 6, "user_id": p6.id, "slot": "Completed", "disease": "Palpitations & Tachycardia",
                "time": "12:00 PM", "date": (today_date - timedelta(days=2)).isoformat(),
                "dept": "Cardiologists", "doctor": "Dr. Rajesh Sharma", "token": 2,
                "diagnosis": "Paroxysmal Supraventricular Tachycardia (PSVT) - Resolved",
                "prescription": "Metoprolol Succinate 25mg OD, reassurance given",
                "notes": "Holter monitor 24h reviewed. Occasional PACs noted. Advised reduction in caffeine intake.",
                "meds": [
                    ("Metoprolol Succinate", "25mg", "Oral", "1-0-0", "30 days", "Morning after meal")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "card"
            },
            {
                "apt_id": 7, "user_id": p7.id, "slot": "Completed", "disease": "Viral Pharyngitis & Cervical Lymphadenitis",
                "time": "04:15 PM", "date": (today_date - timedelta(days=2)).isoformat(),
                "dept": "Infectious Disease", "doctor": "Dr. Vikram Verma", "token": 3,
                "diagnosis": "Acute Follicular Pharyngitis, viral etiology",
                "prescription": "Paracetamol 650mg SOS, Warm saline gargles TDS, Chlorhexidine mouthwash",
                "notes": "Throat swab negative for Group A Strep. Hydration encouraged.",
                "meds": [
                    ("Paracetamol", "650mg", "Oral", "1-0-1", "5 days", "SOS for fever > 100 F"),
                    ("Chlorhexidine Gargle", "15ml", "Oral Rinse", "1-0-1", "7 days", "Swish and spit")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "cash"
            },
            {
                "apt_id": 8, "user_id": p8.id, "slot": "Completed", "disease": "Tinea Corporis & Cruris",
                "time": "09:45 AM", "date": (today_date - timedelta(days=1)).isoformat(),
                "dept": "Dermatologists", "doctor": "Dr. Ananya Patel", "token": 1,
                "diagnosis": "Dermatophytosis (Tinea Corporis et Cruris)",
                "prescription": "Itraconazole 100mg BD after heavy meals for 2 weeks, Luliconazole 1% cream OD",
                "notes": "KOH mount positive for fungal hyphae. Strict hygiene advised.",
                "meds": [
                    ("Itraconazole", "100mg", "Oral", "1-0-1", "14 days", "Immediately after full meal"),
                    ("Luliconazole 1% Cream", "30g", "Topical", "0-0-1", "21 days", "Apply 2cm beyond margin")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "upi"
            },

            # --- TODAY'S LIVE CLINICAL QUEUE ---
            # Doctor 1: Dr. Rajesh Sharma (Cardiology)
            {
                "apt_id": 9, "user_id": p1.id, "slot": "Attended", "disease": "Hypertension BP Monitoring",
                "time": "09:30 AM", "date": today_str,
                "dept": "Cardiologists", "doctor": "Dr. Rajesh Sharma", "token": 1,
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "upi"
            },
            {
                "apt_id": 10, "user_id": p4.id, "slot": "Scheduled", "disease": "Post-Prandial Angina Follow-up",
                "time": "11:00 AM", "date": today_str,
                "dept": "Cardiologists", "doctor": "Dr. Rajesh Sharma", "token": 2,
                "bill_amt": Decimal('500.00'), "bill_status": "Unpaid"
            },
            {
                "apt_id": 11, "user_id": p6.id, "slot": "Scheduled", "disease": "Routine Cardiac Stress Test Review",
                "time": "02:30 PM", "date": today_str,
                "dept": "Cardiologists", "doctor": "Dr. Rajesh Sharma", "token": 3,
                "bill_amt": Decimal('500.00'), "bill_status": "Unpaid"
            },

            # Doctor 2: Dr. Ananya Patel (Dermatology)
            {
                "apt_id": 12, "user_id": p2.id, "slot": "Completed", "disease": "Atopic Dermatitis Follow-up & VIP Admission",
                "time": "10:00 AM", "date": today_str,
                "dept": "Dermatologists", "doctor": "Dr. Ananya Patel", "token": 1,
                "diagnosis": "Erythroderma Secondary to Atopic Eczema, Exudative Lesions",
                "prescription": "Admitted to VIP Room 301 for intense barrier repair, wet wrap therapy, and phototherapy.",
                "notes": "Patient admitted to VIP 301. Currently cleared by doctor for discharge; awaiting inpatient bill settlement.",
                "meds": [
                    ("Clobetasol Propionate", "0.05%", "Topical", "1-0-0", "5 days", "Under occlusion"),
                    ("Cetirizine", "10mg", "Oral", "0-0-1", "10 days", "Bedtime")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "card"
            },
            {
                "apt_id": 13, "user_id": p5.id, "slot": "Attended", "disease": "Severe Psoriatic Nail Dystrophy",
                "time": "11:30 AM", "date": today_str,
                "dept": "Dermatologists", "doctor": "Dr. Ananya Patel", "token": 2,
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "cash"
            },
            {
                "apt_id": 14, "user_id": p7.id, "slot": "Scheduled", "disease": "Contact Dermatitis to Hair Dye",
                "time": "03:00 PM", "date": today_str,
                "dept": "Dermatologists", "doctor": "Dr. Ananya Patel", "token": 3,
                "bill_amt": Decimal('500.00'), "bill_status": "Unpaid"
            },

            # Doctor 3: Dr. Vikram Verma (Infectious Disease & ICU)
            {
                "apt_id": 15, "user_id": p3.id, "slot": "Completed", "disease": "ICU Ward Round & Viral Pneumonia",
                "time": "10:30 AM", "date": today_str,
                "dept": "Infectious Disease", "doctor": "Dr. Vikram Verma", "token": 1,
                "diagnosis": "Viral Bronchopneumonia, Hypoxemic Respiratory Distress (Improving)",
                "prescription": "Oxygen 2L via nasal cannula, IV Ceftriaxone 1g BD, Nebulization with Budecort BD",
                "notes": "Bedside rounds conducted in ICU Bed 201. Afebrile. SpO2 97% on 2L O2. Monitored care continuing.",
                "meds": [
                    ("Ceftriaxone IV", "1g", "IV", "1-0-1", "5 days", "IV over 30 mins"),
                    ("Budecort Respules", "0.5mg", "Nebulization", "1-0-1", "5 days", "Nebulize with 2ml saline")
                ],
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "upi"
            },
            {
                "apt_id": 16, "user_id": p8.id, "slot": "Attended", "disease": "Pyrexia of Unknown Origin (Day 5)",
                "time": "12:00 PM", "date": today_str,
                "dept": "Infectious Disease", "doctor": "Dr. Vikram Verma", "token": 2,
                "bill_amt": Decimal('500.00'), "bill_status": "Paid", "payment_mode": "cash"
            },
            {
                "apt_id": 17, "user_id": p1.id, "slot": "Scheduled", "disease": "Routine Comprehensive Health Checkup",
                "time": "04:00 PM", "date": today_str,
                "dept": "Infectious Disease", "doctor": "Dr. Vikram Verma", "token": 3,
                "bill_amt": Decimal('500.00'), "bill_status": "Unpaid"
            },

            # --- UPCOMING SCHEDULED VISITS (Next Days) ---
            {
                "apt_id": 18, "user_id": p1.id, "slot": "Scheduled", "disease": "Cardiology Post-medication Follow-up",
                "time": "10:00 AM", "date": (today_date + timedelta(days=1)).isoformat(),
                "dept": "Cardiologists", "doctor": "Dr. Rajesh Sharma", "token": 1,
                "bill_amt": Decimal('500.00'), "bill_status": "Unpaid"
            },
            {
                "apt_id": 19, "user_id": p2.id, "slot": "Scheduled", "disease": "Dermatology Patch Testing Review",
                "time": "11:30 AM", "date": (today_date + timedelta(days=1)).isoformat(),
                "dept": "Dermatologists", "doctor": "Dr. Ananya Patel", "token": 2,
                "bill_amt": Decimal('500.00'), "bill_status": "Unpaid"
            },
            {
                "apt_id": 20, "user_id": p4.id, "slot": "Scheduled", "disease": "Endoscopy Report Evaluation",
                "time": "02:00 PM", "date": (today_date + timedelta(days=2)).isoformat(),
                "dept": "Infectious Disease", "doctor": "Dr. Vikram Verma", "token": 1,
                "bill_amt": Decimal('500.00'), "bill_status": "Unpaid"
            },
            {
                "apt_id": 21, "user_id": p5.id, "slot": "Scheduled", "disease": "Biologic Therapy Consultation",
                "time": "11:00 AM", "date": (today_date + timedelta(days=3)).isoformat(),
                "dept": "Dermatologists", "doctor": "Dr. Ananya Patel", "token": 1,
                "bill_amt": Decimal('500.00'), "bill_status": "Unpaid"
            },
            {
                "apt_id": 22, "user_id": p6.id, "slot": "Scheduled", "disease": "Lipid Profile & Statins Titration",
                "time": "10:30 AM", "date": (today_date + timedelta(days=4)).isoformat(),
                "dept": "Cardiologists", "doctor": "Dr. Rajesh Sharma", "token": 1,
                "bill_amt": Decimal('500.00'), "bill_status": "Unpaid"
            }
        ]

        # Insert Appointments & Associated Clinical Records & Bills
        for data in appointments_data:
            apt = Appointments(
                apt_id=data["apt_id"],
                user_id=data["user_id"],
                slot=data["slot"],
                disease=data["disease"],
                time=data["time"],
                date=data["date"],
                dept=data["dept"],
                doctor=data["doctor"],
                token_number=data["token"]
            )
            db.session.add(apt)
            db.session.flush()

            # Medical Record if Completed
            if data.get("diagnosis"):
                rec = MedicalRecord(
                    apt_id=apt.apt_id,
                    diagnosis=data["diagnosis"],
                    prescription=data["prescription"],
                    notes=data.get("notes", ""),
                    status='Signed',
                    signed_by=data["doctor"],
                    signed_at=datetime.strptime(f"{data['date']} 11:30:00", "%Y-%m-%d %H:%M:%S")
                )
                db.session.add(rec)
                db.session.flush()

                # Prescription Items
                for med in data.get("meds", []):
                    item = PrescriptionItem(
                        record_id=rec.record_id,
                        drug_name=med[0],
                        dosage=med[1],
                        route=med[2],
                        frequency=med[3],
                        duration=med[4],
                        instructions=med[5]
                    )
                    db.session.add(item)

                # Add sample Clinical Note Revision on Appointment 1 to demonstrate audit trail
                if data["apt_id"] == 1:
                    rev = ClinicalNoteRevision(
                        record_id=rec.record_id,
                        amended_by=data["doctor"],
                        previous_diagnosis="Essential Hypertension Stage I",
                        previous_prescription="Amlodipine 5mg OD",
                        new_diagnosis="Essential Hypertension Stage II, Stable Angina",
                        new_prescription="Telmisartan 40mg OD, Atorvastatin 20mg HS, Aspirin 75mg OD after breakfast",
                        amendment_reason="Updated post-treadmill test findings and home BP log review",
                        amended_at=datetime.utcnow() - timedelta(days=5)
                    )
                    db.session.add(rev)

            # Billing Record
            bill = Billing(
                apt_id=apt.apt_id,
                user_id=data["user_id"],
                amount=data["bill_amt"],
                status=data["bill_status"],
                issued_on=datetime.strptime(f"{data['date']} 09:00:00", "%Y-%m-%d %H:%M:%S"),
                paid_on=datetime.strptime(f"{data['date']} 09:15:00", "%Y-%m-%d %H:%M:%S") if data["bill_status"] == 'Paid' else None,
                payment_mode=data.get("payment_mode", "upi" if data["bill_status"] == 'Paid' else None),
                transaction_ref=f"TXN-{data['date'].replace('-', '')}-{apt.apt_id:04d}" if data["bill_status"] == 'Paid' else None,
                settled_by="Online Payment" if data.get("payment_mode") in ('upi', 'card', 'netbanking') else ("Frontdesk Cashier" if data.get("payment_mode") == 'cash' else None)
            )
            db.session.add(bill)

        db.session.flush()

        # -------------------------------------------------------------
        # 5. INPATIENT ADMISSIONS ACROSS WARDS (Diverse Lifecycle States)
        # -------------------------------------------------------------

        # Admission A: Historical Discharged Inpatient (Aarav Mehta in Room 101)
        adm_hist = Admission(
            admission_id=1,
            apt_id=1,
            patient_id=p1.id,
            doctor_id=doc1.did,
            room_id=r1.room_id,
            admission_date=datetime.utcnow() - timedelta(days=6),
            discharge_date=datetime.utcnow() - timedelta(days=3),
            status='Discharged',
            tentative_days=3,
            actual_days=3,
            discharge_approved=True,
            discharge_approved_at=datetime.utcnow() - timedelta(days=3, hours=2),
            discharge_summary="Patient presented with hypertensive urgency and anginal symptoms. Managed with IV nitrates and antihypertensive titration. Clinically stable with BP 122/80 mmHg upon discharge.",
            discharge_requested=False
        )
        db.session.add(adm_hist)

        # Admission B: Active Monitored Inpatient in ICU (Sunil Deshmukh in Room 201)
        adm_active = Admission(
            admission_id=2,
            apt_id=3,
            patient_id=p3.id,
            doctor_id=doc3.did,
            room_id=r3.room_id,
            admission_date=datetime.utcnow() - timedelta(days=2),
            status='Admitted',
            tentative_days=4,
            actual_days=None,
            discharge_approved=False,
            discharge_requested=False,
            stay_extended_notes=None
        )
        db.session.add(adm_active)

        # Admission C: Checkout / Fees Remaining Stage (Pooja Nair in VIP Room 301)
        # Doctor Dr. Ananya Patel has clinically approved discharge today. Room rent invoice of 3 days @ 5000 = 15000 is pending checkout settlement.
        adm_pending = Admission(
            admission_id=3,
            apt_id=12,
            patient_id=p2.id,
            doctor_id=doc2.did,
            room_id=r4.room_id,
            admission_date=datetime.utcnow() - timedelta(days=3),
            status='Billing Pending',
            tentative_days=3,
            actual_days=3,
            discharge_approved=True,
            discharge_approved_at=datetime.utcnow() - timedelta(hours=2),
            discharge_summary="Erythroderma and acute eczema completely resolved under monitored wet-wrap protocol and systemic antihistamines. Vitals normal, afebrile, cleared for discharge. Advised topical barrier care.",
            discharge_requested=False
        )
        db.session.add(adm_pending)

        # Inpatient Room Bill for Admission C (VIP Room 301: ₹15,000 Unpaid)
        # Updates appointment 12 billing to reflect the generated room rent invoice awaiting checkout payment
        bill_vip = Billing.query.filter_by(apt_id=12).first()
        if bill_vip:
            bill_vip.amount = Decimal('15000.00')
            bill_vip.status = 'Unpaid'
            bill_vip.payment_mode = None
            bill_vip.transaction_ref = None

        db.session.flush()

        # -------------------------------------------------------------
        # 6. EXTENSIVE AUDIT LOGS (Clinically Chronological History)
        # -------------------------------------------------------------
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        audit_events = [
            (None, admin.id, "SYSTEM BOOT: Dr. Hedgewar Memorial Hospital & Research Centre HIS initialized", (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')),
            (1, p1.id, "APPOINTMENT BOOKED: Cardiology consultation with Dr. Rajesh Sharma", (datetime.now() - timedelta(days=6, hours=4)).strftime('%Y-%m-%d %H:%M:%S')),
            (1, doc1_user.id, "CLINICAL ENCOUNTER COMPLETED: Vitals BP 154/96 recorded by Dr. Rajesh Sharma", (datetime.now() - timedelta(days=6, hours=2)).strftime('%Y-%m-%d %H:%M:%S')),
            (1, doc1_user.id, "INPATIENT ADMISSION CREATED: Patient Aarav Mehta admitted to Room 101 (Tentative: 3 days)", (datetime.now() - timedelta(days=6, hours=1)).strftime('%Y-%m-%d %H:%M:%S')),
            (1, doc1_user.id, "CLINICAL DISCHARGE APPROVED: Dr. Rajesh Sharma signed discharge summary for Room 101", (datetime.now() - timedelta(days=3, hours=2)).strftime('%Y-%m-%d %H:%M:%S')),
            (1, p1.id, "INPATIENT ROOM SETTLEMENT: Rs. 2400.00 paid via UPI (TXN-20261114-0001)", (datetime.now() - timedelta(days=3, hours=1)).strftime('%Y-%m-%d %H:%M:%S')),
            (1, admin.id, "FINAL BED RELEASE CONFIRMED: Room 101 (General Ward) marked Available", (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')),
            
            (3, p3.id, "APPOINTMENT BOOKED: Urgent consultation with Dr. Vikram Verma", (datetime.now() - timedelta(days=2, hours=6)).strftime('%Y-%m-%d %H:%M:%S')),
            (3, doc3_user.id, "INPATIENT ADMISSION CREATED: Patient Sunil Deshmukh admitted to ICU Room 201 (Tentative: 4 days)", (datetime.now() - timedelta(days=2, hours=3)).strftime('%Y-%m-%d %H:%M:%S')),
            (3, p3.id, "INPATIENT CARE ACTIVE: Monitored telemetry and SpO2 tracking initiated in ICU Bed 201", (datetime.now() - timedelta(days=1, hours=12)).strftime('%Y-%m-%d %H:%M:%S')),
            
            (12, p2.id, "APPOINTMENT BOOKED: Dermatology VIP Consultation with Dr. Ananya Patel", (datetime.now() - timedelta(days=3, hours=4)).strftime('%Y-%m-%d %H:%M:%S')),
            (12, doc2_user.id, "INPATIENT ADMISSION CREATED: Patient Pooja Nair admitted to VIP Suite 301", (datetime.now() - timedelta(days=3, hours=2)).strftime('%Y-%m-%d %H:%M:%S')),
            (12, doc2_user.id, "CLINICAL DISCHARGE APPROVED: Dr. Ananya Patel cleared Patient Pooja Nair. Inpatient invoice of Rs. 15,000 generated.", (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')),
            
            (9, p1.id, "OPD CHECK-IN: Patient Aarav Mehta checked in for Dr. Rajesh Sharma queue (Token #1)", (datetime.now() - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')),
            (10, p4.id, "OPD APPOINTMENT SCHEDULED: Patient Mayur Wakchaure scheduled with Dr. Rajesh Sharma (Token #2)", (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')),
            (15, doc3_user.id, "WARD ROUND NOTE: Bedside evaluation of ICU Room 201 conducted by Dr. Vikram Verma", (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')),
            (None, admin.id, "SECURITY AUDIT: Multi-doctor synthetic registry synchronized successfully", now_str)
        ]

        for apt_id, user_id, action, timestamp in audit_events:
            audit = AuditLog(
                apt_id=apt_id,
                user_id=user_id,
                action=action,
                timestamp=timestamp
            )
            db.session.add(audit)

        db.session.commit()
        print("Successfully seeded large synthetic test logs and accounts for Hedgewar Hospital!")

if __name__ == '__main__':
    seed_synthetic_data(force=True)
