from datetime import time

from hms.extensions import db
from hms.models.base import TimestampMixin


class DoctorSchedule(TimestampMixin, db.Model):
    __tablename__ = 'doctor_schedule'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False, index=True)
    weekday = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False, default=time(9, 0))
    end_time = db.Column(db.Time, nullable=False, default=time(17, 0))
    slot_minutes = db.Column(db.Integer, nullable=False, default=30)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    breaks = db.relationship('DoctorBreak', backref='schedule', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f"<DoctorSchedule doc={self.doctor_id} weekday={self.weekday}>"

class DoctorBreak(TimestampMixin, db.Model):
    __tablename__ = 'doctor_break'

    id = db.Column(db.Integer, primary_key=True)
    doctor_schedule_id = db.Column(db.Integer, db.ForeignKey('doctor_schedule.id', ondelete='CASCADE'), nullable=False)
    start_time = db.Column(db.Time, nullable=False, default=time(13, 0))
    end_time = db.Column(db.Time, nullable=False, default=time(14, 0))
    reason = db.Column(db.String(100), default='Lunch / Rest')

class DoctorLeave(TimestampMixin, db.Model):
    __tablename__ = 'doctor_leave'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False, index=True)
    date_from = db.Column(db.Date, nullable=False)
    date_to = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Approved', nullable=False)  # Approved, Pending, Rejected

    def __repr__(self) -> str:
        return f"<DoctorLeave doc={self.doctor_id} {self.date_from} to {self.date_to}>"
