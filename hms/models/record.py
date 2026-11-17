from hms.extensions import db
from hms.models.base import TimestampMixin


class MedicalRecord(TimestampMixin, db.Model):
    __tablename__ = 'medical_record'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='RESTRICT'), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), nullable=True, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='RESTRICT'), nullable=True, index=True)

    diagnosis = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)  # Legacy text field retained for parity
    is_latest = db.Column(db.Boolean, default=True, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)

    # Structured relationships
    prescription_items = db.relationship('PrescriptionItem', backref='record', cascade='all, delete-orphan')
    versions = db.relationship('MedicalRecordVersion', backref='record', cascade='all, delete-orphan')

    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('medical_records', lazy='dynamic'))
    doctor = db.relationship('Doctor', foreign_keys=[doctor_id], backref=db.backref('medical_records', lazy='dynamic'))

    # Legacy synonyms
    record_id = db.synonym('id')
    apt_id = db.synonym('appointment_id')

    def __init__(self, **kwargs):
        if 'record_id' in kwargs and 'id' not in kwargs:
            kwargs['id'] = kwargs.pop('record_id')
        if 'apt_id' in kwargs and 'appointment_id' not in kwargs:
            kwargs['appointment_id'] = kwargs.pop('apt_id')
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<MedicalRecord {self.id} for Apt {self.appointment_id} (v{self.version})>"


class PrescriptionItem(TimestampMixin, db.Model):
    __tablename__ = 'prescription_item'

    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('medical_record.id', ondelete='CASCADE'), nullable=False, index=True)
    medicine = db.Column(db.String(150), nullable=False)
    dose = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    instructions = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PrescriptionItem {self.medicine} {self.dose} {self.frequency}>"


class MedicalRecordVersion(TimestampMixin, db.Model):
    __tablename__ = 'medical_record_version'

    id = db.Column(db.Integer, primary_key=True)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_record.id', ondelete='CASCADE'), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)
    amended_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    amendment_reason = db.Column(db.Text, nullable=True)

    amender = db.relationship('User', foreign_keys=[amended_by])

    def __repr__(self) -> str:
        return f"<MedicalRecordVersion {self.id}: Record {self.medical_record_id} v{self.version}>"
