from datetime import datetime

from sqlalchemy import func
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.expression import FunctionElement

from hms.extensions import db
from hms.models.base import SoftDeleteMixin, TimestampMixin


class DateStr(str):
    def __eq__(self, other):
        from datetime import date as dt_date
        if isinstance(other, dt_date):
            return str(self) == other.isoformat()
        return super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)


class ActiveSlotExpr(FunctionElement):
    name = 'active_slot_expr'

@compiles(ActiveSlotExpr, 'mysql')
def compile_mysql(element, compiler, **kw):
    return "CASE WHEN status IN ('Cancelled', 'Missed') THEN NULL ELSE CONCAT(doctor_id, '|', DATE_FORMAT(starts_at, '%%Y-%%m-%%d %%H:%%i')) END"

@compiles(ActiveSlotExpr, 'sqlite')
def compile_sqlite(element, compiler, **kw):
    return "CASE WHEN status IN ('Cancelled', 'Missed') THEN NULL ELSE CAST(doctor_id AS TEXT) || '|' || starts_at END"

@compiles(ActiveSlotExpr)
def compile_default(element, compiler, **kw):
    return "CASE WHEN status IN ('Cancelled', 'Missed') THEN NULL ELSE CONCAT(doctor_id, '|', DATE_FORMAT(starts_at, '%%Y-%%m-%%d %%H:%%i')) END"


class AppointmentStatus:
    SCHEDULED = 'Scheduled'
    CHECKED_IN = 'CheckedIn'
    COMPLETED = 'Completed'
    CANCELLED = 'Cancelled'
    MISSED = 'Missed'

    ALL = (SCHEDULED, CHECKED_IN, COMPLETED, CANCELLED, MISSED)


class Appointment(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='RESTRICT'), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='RESTRICT'), nullable=True, index=True)

    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    duration_min = db.Column(db.Integer, default=30, nullable=False)
    status = db.Column(db.String(20), default=AppointmentStatus.SCHEDULED, nullable=False, index=True)

    reason = db.Column(db.Text, nullable=True)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    cancel_reason = db.Column(db.String(255), nullable=True)

    # Generated column for double-booking prevention (D-03)
    active_slot_key = db.Column(
        db.String(64),
        db.Computed(ActiveSlotExpr(), persisted=True),
        unique=True,
        index=True
    )

    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('appointments', lazy='dynamic'))
    doctor_rel = db.relationship('Doctor', foreign_keys=[doctor_id], backref=db.backref('appointments', lazy='dynamic'))
    department = db.relationship('Department', foreign_keys=[department_id])
    canceller = db.relationship('User', foreign_keys=[cancelled_by])
    records = db.relationship('MedicalRecord', backref='appointment', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='appointment', lazy='dynamic')

    # D-11 Composite Indexes
    __table_args__ = (
        db.Index('ix_patient_starts_at', 'patient_id', 'starts_at'),
        db.Index('ix_doctor_starts_at', 'doctor_id', 'starts_at'),
    )

    # Legacy synonyms & property adapters
    apt_id = db.synonym('id')
    user_id = db.synonym('patient_id')
    slot = db.synonym('status')
    disease = db.synonym('reason')

    def __init__(self, **kwargs):
        if 'user_id' in kwargs and 'patient_id' not in kwargs:
            kwargs['patient_id'] = kwargs.pop('user_id')
        if 'apt_id' in kwargs and 'id' not in kwargs:
            kwargs['id'] = kwargs.pop('apt_id')
        if 'slot' in kwargs and 'status' not in kwargs:
            kwargs['status'] = kwargs.pop('slot')
        if 'disease' in kwargs and 'reason' not in kwargs:
            kwargs['reason'] = kwargs.pop('disease')
        if 'starts_at' not in kwargs:
            d_val = kwargs.pop('date', None)
            t_val = kwargs.pop('time', None)
            if d_val and t_val:
                try:
                    from datetime import date as dt_date
                    from datetime import time as dt_time
                    t_str = str(t_val).strip()
                    if 'AM' in t_str or 'PM' in t_str:
                        parsed_t = datetime.strptime(t_str, '%I:%M %p').time()
                    else:
                        parts = t_str.split(':')
                        parsed_t = dt_time(int(parts[0]), int(parts[1]))
                    parsed_d = dt_date.fromisoformat(str(d_val)) if isinstance(d_val, str) else d_val
                    kwargs['starts_at'] = datetime.combine(parsed_d, parsed_t)
                except (ValueError, TypeError):
                    kwargs['starts_at'] = datetime.now()
            else:
                kwargs['starts_at'] = datetime.now()
        if 'doctor_id' not in kwargs:
            kwargs.pop('doctor', None)
            kwargs['doctor_id'] = 1
        kwargs.pop('dept', None)
        valid_attrs = {col.name for col in self.__table__.columns}
        valid_attrs.update({'patient', 'doctor_rel', 'canceller', 'records', 'invoices'})
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_attrs or hasattr(self.__class__, k)}
        super().__init__(**filtered_kwargs)

    @property
    def dept(self) -> str:
        if self.department:
            return self.department.name
        if self.doctor_rel and self.doctor_rel.department:
            return self.doctor_rel.department.name
        return ''

    @property
    def doctor(self) -> str:
        if self.doctor_rel and self.doctor_rel.user:
            return self.doctor_rel.user.username
        return ''

    @doctor.setter
    def doctor(self, val):
        # Compatibility with legacy code setting apt.doctor = name string
        pass

    @hybrid_property
    def date(self) -> str:
        return DateStr(self.starts_at.strftime('%Y-%m-%d')) if self.starts_at else ''

    @date.expression
    def date(cls):
        return func.date(cls.starts_at)

    @date.setter
    def date(self, val):
        pass

    @hybrid_property
    def time(self) -> str:
        return self.starts_at.strftime('%I:%M %p') if self.starts_at else ''

    @time.expression
    def time(cls):
        return func.time(cls.starts_at)

    @time.setter
    def time(self, val):
        pass

    def __repr__(self) -> str:
        return f"<Appointment {self.id}: Doc {self.doctor_id}, Patient {self.patient_id}, {self.starts_at} ({self.status})>"
