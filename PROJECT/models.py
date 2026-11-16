from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

# ─────────────────────────────────────────────
# Database Models
# ─────────────────────────────────────────────

class Test(db.Model):
    __tablename__ = 'test'
    id    = db.Column(db.Integer, primary_key=True)
    name  = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    usertype = db.Column(db.String(50), nullable=False) # 'Admin', 'Doctor', 'Patient', 'Receptionist', 'Cashier'
    email    = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(1000), nullable=False)
    phone    = db.Column(db.String(12), nullable=True)  
    gender   = db.Column(db.String(20), nullable=True)
    
    # Clinical Identity Extensions
    mrn         = db.Column(db.String(50), unique=True, nullable=True) # Medical Record Number for patients
    allergies   = db.Column(db.String(255), default='None known')
    blood_group = db.Column(db.String(10), nullable=True)
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    appointments = db.relationship('Appointments', backref='patient', lazy=True, cascade="all, delete-orphan")
    doctor_profile = db.relationship('Doctors', backref='user_account', uselist=False, cascade="all, delete-orphan")


class Appointments(db.Model):
    __tablename__ = 'appointments'
    apt_id  = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    slot    = db.Column(db.String(50), nullable=False, default='Scheduled') # 'Scheduled', 'CheckedIn', 'Attended', 'Completed', 'Missed', 'Cancelled'
    disease = db.Column(db.String(150), nullable=False) # Chief complaint
    time    = db.Column(db.String(50), nullable=False)
    date    = db.Column(db.String(50), nullable=False)
    dept    = db.Column(db.String(50), nullable=False)
    doctor  = db.Column(db.String(100), nullable=False)
    token_number = db.Column(db.Integer, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    medical_record = db.relationship('MedicalRecord', backref='appointment', uselist=False, cascade="all, delete-orphan")


class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'
    record_id    = db.Column(db.Integer, primary_key=True)
    apt_id       = db.Column(db.Integer, db.ForeignKey('appointments.apt_id', ondelete='CASCADE'), nullable=False)
    diagnosis    = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=False)
    notes        = db.Column(db.Text)
    status       = db.Column(db.String(20), default='Signed') # 'Draft', 'Signed', 'Amended'
    signed_by    = db.Column(db.String(100), nullable=True)
    signed_at    = db.Column(db.DateTime, nullable=True)
    created_at   = db.Column(db.DateTime, server_default=db.func.now())

    # Revisions and structured items
    revisions          = db.relationship('ClinicalNoteRevision', backref='record', lazy=True, cascade="all, delete-orphan")
    prescription_items = db.relationship('PrescriptionItem', backref='record', lazy=True, cascade="all, delete-orphan")


class ClinicalNoteRevision(db.Model):
    """Immutable audit trail for every signed medical record modification."""
    __tablename__ = 'clinical_note_revisions'
    revision_id           = db.Column(db.Integer, primary_key=True)
    record_id             = db.Column(db.Integer, db.ForeignKey('medical_records.record_id', ondelete='CASCADE'), nullable=False)
    amended_by            = db.Column(db.String(100), nullable=False)
    previous_diagnosis    = db.Column(db.Text, nullable=False)
    previous_prescription = db.Column(db.Text, nullable=False)
    new_diagnosis         = db.Column(db.Text, nullable=False)
    new_prescription      = db.Column(db.Text, nullable=False)
    amendment_reason      = db.Column(db.Text, nullable=False)
    amended_at            = db.Column(db.DateTime, default=datetime.utcnow)


class PrescriptionItem(db.Model):
    """Structured clinical medication items (dose, route, frequency, duration)."""
    __tablename__ = 'prescription_items'
    item_id      = db.Column(db.Integer, primary_key=True)
    record_id    = db.Column(db.Integer, db.ForeignKey('medical_records.record_id', ondelete='CASCADE'), nullable=False)
    drug_name    = db.Column(db.String(150), nullable=False)
    dosage       = db.Column(db.String(50), nullable=False)
    route        = db.Column(db.String(50), default='Oral')
    frequency    = db.Column(db.String(50), default='1-0-1')
    duration     = db.Column(db.String(50), default='5 days')
    instructions = db.Column(db.String(200), default='After food')


class Doctors(db.Model):
    __tablename__ = 'doctors'
    did     = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    dept    = db.Column(db.String(100), nullable=False)


class AuditLog(db.Model): 
    __tablename__ = 'audit_log'
    tid       = db.Column(db.Integer, primary_key=True)
    apt_id    = db.Column(db.Integer, nullable=True)
    user_id   = db.Column(db.Integer, nullable=False) 
    action    = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.String(50), nullable=False)


class Billing(db.Model):
    __tablename__ = 'billing'
    bill_id      = db.Column(db.Integer, primary_key=True)
    apt_id       = db.Column(db.Integer, db.ForeignKey('appointments.apt_id', ondelete='CASCADE'), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    amount       = db.Column(db.Numeric(10, 2), nullable=False, default=500.00)
    status       = db.Column(db.String(20), nullable=False, default='Unpaid') # 'Unpaid', 'Paid', 'Refunded', 'Cancelled'
    issued_on    = db.Column(db.DateTime, server_default=db.func.now())
    paid_on      = db.Column(db.DateTime, nullable=True)
    payment_mode = db.Column(db.String(50), nullable=True) # 'cash', 'upi', 'card', 'netbanking', 'demo_simulation'
    bank_name    = db.Column(db.String(100), nullable=True)
    transaction_ref = db.Column(db.String(100), nullable=True)
    settled_by   = db.Column(db.String(100), nullable=True)

    appointment = db.relationship('Appointments', backref=db.backref('billing', uselist=False))


# ── Inpatient Room & Ward Management ─────────────────────────────────

class Room(db.Model):
    __tablename__ = 'rooms'
    room_id      = db.Column(db.Integer, primary_key=True)
    room_number  = db.Column(db.String(10), unique=True, nullable=False)
    ward_type    = db.Column(db.String(50), nullable=False) # 'General', 'ICU', 'VIP', 'Maternity'
    rate_per_day = db.Column(db.Numeric(10, 2), nullable=False)
    status       = db.Column(db.String(20), nullable=False, default='Available') # 'Available', 'Occupied', 'Cleaning', 'Maintenance'

    admissions = db.relationship('Admission', backref='room', lazy=True)


class Admission(db.Model):
    __tablename__ = 'admissions'
    admission_id   = db.Column(db.Integer, primary_key=True)
    apt_id         = db.Column(db.Integer, db.ForeignKey('appointments.apt_id', ondelete='CASCADE'), nullable=False)
    patient_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    doctor_id      = db.Column(db.Integer, db.ForeignKey('doctors.did', ondelete='CASCADE'), nullable=False)
    room_id        = db.Column(db.Integer, db.ForeignKey('rooms.room_id', ondelete='CASCADE'), nullable=False)
    admission_date = db.Column(db.DateTime, server_default=db.func.now())
    discharge_date = db.Column(db.DateTime, nullable=True)
    status         = db.Column(db.String(30), nullable=False, default='Admitted') # 'Admitted', 'Billing Pending', 'Discharged'
    discharge_summary = db.Column(db.Text, nullable=True)
    discharge_requested = db.Column(db.Boolean, default=False)
    discharge_requested_at = db.Column(db.DateTime, nullable=True)
    discharge_notes = db.Column(db.String(255), nullable=True)
    
    # Inpatient Stay & Lifecycle Extensions
    tentative_days             = db.Column(db.Integer, default=3)
    discharge_approved         = db.Column(db.Boolean, default=False)
    discharge_approved_at      = db.Column(db.DateTime, nullable=True)
    discharge_rejection_reason = db.Column(db.String(255), nullable=True)
    actual_days                = db.Column(db.Integer, nullable=True)
    stay_extended_notes        = db.Column(db.String(255), nullable=True)

    patient     = db.relationship('User', backref=db.backref('admissions', lazy=True))
    doctor      = db.relationship('Doctors', backref=db.backref('admissions', lazy=True))
    appointment = db.relationship('Appointments', backref=db.backref('admission', uselist=False))
