from decimal import Decimal

from hms.extensions import db
from hms.models.base import SoftDeleteMixin, TimestampMixin


class Doctor(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='RESTRICT'), nullable=True)
    consultation_fee = db.Column(db.Numeric(10, 2), default=Decimal('500.00'), nullable=False)
    qualifications = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    photo_url = db.Column(db.String(255), nullable=True)
    years_experience = db.Column(db.Integer, default=0, nullable=False)

    # Legacy compatibility synonym
    did = db.synonym('id')

    @property
    def user_account(self):
        return self.user

    def __init__(self, **kwargs):
        if 'did' in kwargs and 'id' not in kwargs:
            kwargs['id'] = kwargs.pop('did')
        dept_name = kwargs.pop('dept', None)
        if dept_name and 'department_id' not in kwargs:
            from hms.models.department import Department
            dept_obj = Department.query.filter_by(name=dept_name).first()
            if not dept_obj:
                dept_obj = Department(name=dept_name, code=dept_name[:4].upper())
                db.session.add(dept_obj)
                db.session.flush()
            kwargs['department_id'] = dept_obj.id
        super().__init__(**kwargs)

    @property
    def dept(self) -> str:
        return self.department.name if self.department else ''

    @property
    def name(self) -> str:
        return self.user.username if self.user else ''

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} user_id={self.user_id}>"


# Legacy synonym
Doctors = Doctor
