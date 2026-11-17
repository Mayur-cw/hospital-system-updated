from hms.extensions import db
from hms.models.base import SoftDeleteMixin, TimestampMixin


class Department(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'department'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    doctors = db.relationship('Doctor', backref='department', lazy='dynamic')

    def __repr__(self) -> str:
        return f"<Department {self.code}: {self.name}>"
