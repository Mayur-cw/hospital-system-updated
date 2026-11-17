from datetime import UTC, datetime
from decimal import Decimal

from hms.extensions import db
from hms.models.base import SoftDeleteMixin, TimestampMixin


class RoomStatus:
    AVAILABLE = 'Available'
    OCCUPIED = 'Occupied'
    MAINTENANCE = 'Maintenance'
    ALL = (AVAILABLE, OCCUPIED, MAINTENANCE)

class AdmissionStatus:
    ADMITTED = 'Admitted'
    DISCHARGE_REQUESTED = 'DischargeRequested'
    DISCHARGE_APPROVED = 'DischargeApproved'
    DISCHARGED = 'Discharged'
    ALL = (ADMITTED, DISCHARGE_REQUESTED, DISCHARGE_APPROVED, DISCHARGED)

class Room(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'room'

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    ward_type = db.Column(db.String(50), nullable=False)
    rate_per_day = db.Column(db.Numeric(10, 2), default=Decimal('1000.00'), nullable=False)
    status = db.Column(db.String(20), default=RoomStatus.AVAILABLE, nullable=False, index=True)

    admissions = db.relationship('Admission', backref='room', lazy='dynamic')

    # Legacy compatibility synonym
    room_id = db.synonym('id')

    def __init__(self, **kwargs):
        if 'room_id' in kwargs and 'id' not in kwargs:
            kwargs['id'] = kwargs.pop('room_id')
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Room {self.room_number} ({self.ward_type}) - {self.status}>"


class Admission(TimestampMixin, db.Model):
    __tablename__ = 'admission'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='RESTRICT'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id', ondelete='RESTRICT'), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='SET NULL'), nullable=True, index=True)

    admission_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    discharge_date = db.Column(db.DateTime, nullable=True)
    tentative_days = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(30), default=AdmissionStatus.ADMITTED, nullable=False, index=True)
    discharge_notes = db.Column(db.Text, nullable=True)

    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('admissions', lazy='dynamic'))
    doctor = db.relationship('Doctor', foreign_keys=[doctor_id], backref=db.backref('admissions', lazy='dynamic'))
    appointment = db.relationship('Appointment', foreign_keys=[appointment_id], backref=db.backref('admissions', lazy='dynamic'))

    # Legacy compatibility synonyms
    admission_id = db.synonym('id')
    apt_id = db.synonym('appointment_id')

    def __init__(self, **kwargs):
        if 'admission_id' in kwargs and 'id' not in kwargs:
            kwargs['id'] = kwargs.pop('admission_id')
        if 'apt_id' in kwargs and 'appointment_id' not in kwargs:
            kwargs['appointment_id'] = kwargs.pop('apt_id')
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Admission {self.id}: Patient {self.patient_id}, Room {self.room_id} ({self.status})>"
