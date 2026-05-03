from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Initialize SQLAlchemy without binding it to the app just yet
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
    usertype = db.Column(db.String(50), nullable=False) 
    email    = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(1000), nullable=False)
    phone    = db.Column(db.String(12), nullable=True)  
    gender   = db.Column(db.String(20), nullable=True)  

    # Establishes a 1-to-Many relationship with Appointments
    appointments = db.relationship('Appointments', backref='patient', lazy=True, cascade="all, delete-orphan")
    
    # 🎓 UPGRADE: Establishes a 1-to-1 relationship with the Doctors table
    doctor_profile = db.relationship('Doctors', backref='user_account', uselist=False, cascade="all, delete-orphan")


class Appointments(db.Model):
    __tablename__ = 'appointments'
    apt_id  = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    slot    = db.Column(db.String(50), nullable=False)
    disease = db.Column(db.String(50), nullable=False)
    time    = db.Column(db.String(50), nullable=False)
    date    = db.Column(db.String(50), nullable=False)
    dept    = db.Column(db.String(50), nullable=False)
    doctor  = db.Column(db.String(50), nullable=False)


class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'
    record_id    = db.Column(db.Integer, primary_key=True)
    apt_id       = db.Column(db.Integer, db.ForeignKey('appointments.apt_id', ondelete='CASCADE'), nullable=False)
    diagnosis    = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=False)
    notes        = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, server_default=db.func.now())


class Doctors(db.Model):
    __tablename__ = 'doctors'
    did     = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    dept    = db.Column(db.String(100), nullable=False)


class AuditLog(db.Model): 
    __tablename__ = 'audit_log'
    tid       = db.Column(db.Integer, primary_key=True)
    apt_id    = db.Column(db.Integer, nullable=False)
    user_id   = db.Column(db.Integer, nullable=False) 
    action    = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.String(50), nullable=False)


class Billing(db.Model):
    __tablename__ = 'billing'
    bill_id = db.Column(db.Integer, primary_key=True)
    apt_id = db.Column(db.Integer, db.ForeignKey('appointments.apt_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=500.00)
    status = db.Column(db.String(20), nullable=False, default='Unpaid')
    issued_on = db.Column(db.DateTime, server_default=db.func.now())
    paid_on = db.Column(db.DateTime, nullable=True)
    payment_mode = db.Column(db.String(50), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)

    appointment = db.relationship('Appointments', backref=db.backref('billing', uselist=False))


# 🏥 NEW MODELS: Inpatient Room Management
class Room(db.Model):
    __tablename__ = 'rooms'
    room_id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False)
    ward_type = db.Column(db.String(50), nullable=False)
    rate_per_day = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Available')

    admissions = db.relationship('Admission', backref='room', lazy=True)

class Admission(db.Model):
    __tablename__ = 'admissions'
    admission_id = db.Column(db.Integer, primary_key=True)
    apt_id = db.Column(db.Integer, db.ForeignKey('appointments.apt_id', ondelete='CASCADE'), nullable=False) # 🚨 NEW
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.did', ondelete='CASCADE'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.room_id', ondelete='CASCADE'), nullable=False)
    admission_date = db.Column(db.DateTime, server_default=db.func.now())
    discharge_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Admitted')

    patient = db.relationship('User', backref=db.backref('admissions', lazy=True))
    doctor = db.relationship('Doctors', backref=db.backref('admissions', lazy=True))
    # 🚨 NEW: Allows us to do invoice.appointment.admission in the receipt!
    appointment = db.relationship('Appointments', backref=db.backref('admission', uselist=False))