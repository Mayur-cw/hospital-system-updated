from hms.extensions import db
from hms.models.base import TimestampMixin


class PatientProfile(TimestampMixin, db.Model):
    __tablename__ = 'patient_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)
    dob = db.Column(db.Date, nullable=True)
    blood_group = db.Column(db.String(10), nullable=True)
    address = db.Column(db.Text, nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    allergies = db.Column(db.Text, nullable=True)
    chronic_conditions = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PatientProfile user_id={self.user_id}>"
