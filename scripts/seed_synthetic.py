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
from models import db, User, Doctors, Appointments, MedicalRecord, Billing, Room, Admission, AuditLog

def seed_synthetic_data():
    app = create_app()
    with app.app_context():
        # Recreate schema cleanly in development mode
        db.create_all()
        
        # Check if already seeded
        if User.query.filter_by(email='admin@hospital.local').first():
            print("Synthetic data already present in database.")
            return

        print("Seeding synthetic users and master data...")

        # 1. Staff Accounts (Admin, Doctors, Receptionist, Cashier)
        admin = User(
            username='Dr. Amit Mehta',
            usertype='Admin',
            email='admin@hospital.local',
            password=generate_password_hash('AdminPass@2026'),
            phone='555-0100',
            gender='Male'
        )
        db.session.add(admin)

        doc1_user = User(
            username='Dr. Rajesh Sharma',
            usertype='Doctor',
            email='dr.sharma@hospital.local',
            password=generate_password_hash('DoctorPass@2026'),
            phone='555-0101',
            gender='Male'
        )
        doc2_user = User(
            username='Dr. Ananya Patel',
            usertype='Doctor',
            email='dr.patel@hospital.local',
            password=generate_password_hash('DoctorPass@2026'),
            phone='555-0102',
            gender='Female'
        )
        doc3_user = User(
            username='Dr. Vikram Verma',
            usertype='Doctor',
            email='dr.verma@hospital.local',
            password=generate_password_hash('DoctorPass@2026'),
            phone='555-0103',
            gender='Male'
        )
        receptionist = User(
            username='Sunita Frontdesk',
            usertype='Receptionist',
            email='receptionist@hospital.local',
            password=generate_password_hash('StaffPass@2026'),
            phone='555-0104',
            gender='Female'
        )
        cashier = User(
            username='Vikram Cashier',
            usertype='Cashier',
            email='cashier@hospital.local',
            password=generate_password_hash('StaffPass@2026'),
            phone='555-0105',
            gender='Male'
        )
        db.session.add_all([doc1_user, doc2_user, doc3_user, receptionist, cashier])
        db.session.flush()

        # Doctor Specialty Profiles
        doc1 = Doctors(did=1, user_id=doc1_user.id, dept='Cardiologists')
        doc2 = Doctors(did=2, user_id=doc2_user.id, dept='Dermatologists')
        doc3 = Doctors(did=3, user_id=doc3_user.id, dept='Infectious Disease')
        db.session.add_all([doc1, doc2, doc3])

        # 2. Synthetic Patients with MRNs
        p1 = User(
            username='Aarav Mehta',
            usertype='Patient',
            email='patient1@hospital.local',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0201',
            gender='Male',
            mrn='MRN-2026-0001',
            allergies='Penicillin allergy (severe rash)',
            blood_group='O+'
        )
        p2 = User(
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
            username='Sunil Deshmukh',
            usertype='Patient',
            email='patient3@hospital.local',
            password=generate_password_hash('PatientPass@2026'),
            phone='555-0203',
            gender='Male',
            mrn='MRN-2026-0003',
            allergies='NSAIDs (Aspirin)',
            blood_group='A+'
        )
        db.session.add_all([p1, p2, p3])
        db.session.flush()

        # 3. Hospital Rooms
        r1 = Room(room_number='101', ward_type='General', rate_per_day=Decimal('800.00'), status='Available')
        r2 = Room(room_number='102', ward_type='General', rate_per_day=Decimal('800.00'), status='Available')
        r3 = Room(room_number='201', ward_type='ICU', rate_per_day=Decimal('3500.00'), status='Occupied')
        r4 = Room(room_number='301', ward_type='VIP', rate_per_day=Decimal('5000.00'), status='Available')
        db.session.add_all([r1, r2, r3, r4])
        db.session.flush()

        # 4. Appointments
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        apt1 = Appointments(
            user_id=p1.id,
            slot='Completed',
            disease='Acute Chest Heaviness',
            time='10:00 AM',
            date=yesterday,
            dept='Cardiologists',
            doctor='Dr. Rajesh Sharma',
            token_number=1
        )
        apt2 = Appointments(
            user_id=p2.id,
            slot='Scheduled',
            disease='Eczema Flare-up',
            time='11:30 AM',
            date=today,
            dept='Dermatologists',
            doctor='Dr. Ananya Patel',
            token_number=2
        )
        apt3 = Appointments(
            user_id=p3.id,
            slot='Attended',
            disease='High Grade Viral Fever',
            time='02:00 PM',
            date=today,
            dept='Infectious Disease',
            doctor='Dr. Vikram Verma',
            token_number=3
        )
        apt4 = Appointments(
            user_id=p1.id,
            slot='Scheduled',
            disease='Cardiology Follow-up',
            time='10:30 AM',
            date=tomorrow,
            dept='Cardiologists',
            doctor='Dr. Rajesh Sharma',
            token_number=1
        )
        db.session.add_all([apt1, apt2, apt3, apt4])
        db.session.flush()

        # 5. Medical Records & Signed Notes
        rec1 = MedicalRecord(
            apt_id=apt1.apt_id,
            diagnosis='Stable Angina Pectoris, Essential Hypertension',
            prescription='Aspirin 75mg OD (morning after meal), Atorvastatin 20mg HS for 30 days',
            notes='ECG normal. Advised lipid profile and 2D Echocardiogram follow-up.',
            status='Signed',
            signed_by='Dr. Rajesh Sharma',
            signed_at=datetime.utcnow() - timedelta(days=1)
        )
        db.session.add(rec1)

        # 6. Active Inpatient Admission for Patient 3 (Sunil in ICU 201)
        adm1 = Admission(
            apt_id=apt3.apt_id,
            patient_id=p3.id,
            doctor_id=doc3.did,
            room_id=r3.room_id,
            admission_date=datetime.utcnow() - timedelta(days=2),
            status='Admitted',
            discharge_summary=None
        )
        db.session.add(adm1)

        # 7. Invoices & Billing
        b1 = Billing(
            apt_id=apt1.apt_id,
            user_id=p1.id,
            amount=Decimal('500.00'),
            status='Paid',
            issued_on=datetime.utcnow() - timedelta(days=1),
            paid_on=datetime.utcnow() - timedelta(days=1),
            payment_mode='cash',
            transaction_ref='CASH-RCPT-001',
            settled_by='Vikram Cashier'
        )
        b2 = Billing(
            apt_id=apt2.apt_id,
            user_id=p2.id,
            amount=Decimal('500.00'),
            status='Unpaid',
            issued_on=datetime.utcnow()
        )
        db.session.add_all([b1, b2])

        # 8. Audit Log
        db.session.add(AuditLog(
            apt_id=apt1.apt_id,
            user_id=admin.id,
            action='SYSTEM INITIALIZED WITH SYNTHETIC DEMO SEED',
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))

        db.session.commit()
        print("Successfully seeded synthetic hospital dataset!")

if __name__ == '__main__':
    seed_synthetic_data()
