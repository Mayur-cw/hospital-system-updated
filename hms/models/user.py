from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from hms.extensions import db
from hms.models.base import SoftDeleteMixin, TimestampMixin


class UserRole:
    ADMIN = 'Admin'
    DOCTOR = 'Doctor'
    PATIENT = 'Patient'
    RECEPTIONIST = 'Receptionist'
    ALL_ROLES = (ADMIN, DOCTOR, PATIENT, RECEPTIONIST)

class User(UserMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    usertype = db.Column(db.String(20), nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)

    # Relationships
    patient_profile = db.relationship('PatientProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    doctor_profile = db.relationship('Doctor', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, raw_password: str) -> None:
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password, raw_password)

    @property
    def is_admin(self) -> bool:
        return self.usertype == UserRole.ADMIN

    @property
    def is_doctor(self) -> bool:
        return self.usertype == UserRole.DOCTOR

    @property
    def is_patient(self) -> bool:
        return self.usertype == UserRole.PATIENT

    @property
    def is_receptionist(self) -> bool:
        return self.usertype == UserRole.RECEPTIONIST

    def __repr__(self) -> str:
        return f"<User {self.id}: {self.username} ({self.usertype})>"
