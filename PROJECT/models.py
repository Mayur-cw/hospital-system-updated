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


class Patients(db.Model):
    __tablename__ = 'patients'
    pid     = db.Column(db.Integer, primary_key=True)
    email   = db.Column(db.String(50), nullable=False)
    name    = db.Column(db.String(50), nullable=False)
    gender  = db.Column(db.String(50), nullable=False)
    slot    = db.Column(db.String(50), nullable=False)
    disease = db.Column(db.String(50), nullable=False)
    time    = db.Column(db.String(50), nullable=False)
    date    = db.Column(db.String(50), nullable=False)
    dept    = db.Column(db.String(50), nullable=False)
    number  = db.Column(db.String(12), nullable=False)
    doctor  = db.Column(db.String(50), nullable=False)

class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'
    record_id    = db.Column(db.Integer, primary_key=True)
    pid          = db.Column(db.Integer, db.ForeignKey('patients.pid', ondelete='CASCADE'), nullable=False)
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


class Trigr(db.Model):
    __tablename__ = 'trigr'
    tid       = db.Column(db.Integer, primary_key=True)
    pid       = db.Column(db.Integer, nullable=False)
    email     = db.Column(db.String(50), nullable=False)
    name      = db.Column(db.String(50), nullable=False)
    action    = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.String(50), nullable=False)