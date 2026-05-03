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

    # 🚨 NEW: Establishes a 1-to-Many relationship with Appointments
    # This allows us to use `appointment.patient.username` or `appointment.patient.phone` in Jinja!
    appointments = db.relationship('Appointments', backref='patient', lazy=True, cascade="all, delete-orphan")


class Appointments(db.Model):
    __tablename__ = 'appointments'
    apt_id  = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False) # 🚨 NEW FOREIGN KEY
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
    did        = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(50), nullable=False)
    doctorname = db.Column(db.String(50), nullable=False)
    dept       = db.Column(db.String(100), nullable=False)


class AuditLog(db.Model): # 🚨 RENAMED FROM Trigr
    __tablename__ = 'audit_log'
    tid       = db.Column(db.Integer, primary_key=True)
    apt_id    = db.Column(db.Integer, nullable=False)
    user_id   = db.Column(db.Integer, nullable=False) # 🚨 REPLACED NAME AND EMAIL
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
    
    # Add these under your existing columns in the Billing class
    payment_mode = db.Column(db.String(50), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)

    # This creates a back-reference so we can do bill.appointment.doctor in Jinja!
    appointment = db.relationship('Appointments', backref=db.backref('billing', uselist=False))