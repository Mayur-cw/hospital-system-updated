from datetime import UTC, datetime

from hms.extensions import db
from hms.models.base import TimestampMixin


class HospitalSetting(TimestampMixin, db.Model):
    __tablename__ = 'hospital_setting'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    @classmethod
    def get(cls, key: str, default: str = '') -> str:
        record = cls.query.filter_by(key=key).first()
        return record.value if record else default

    @classmethod
    def set(cls, key: str, value: str, description: str | None = None) -> 'HospitalSetting':
        record = cls.query.filter_by(key=key).first()
        if not record:
            record = cls(key=key, value=value, description=description)
            db.session.add(record)
        else:
            record.value = value
            if description:
                record.description = description
            record.updated_at = datetime.now(UTC)
        db.session.commit()
        return record

    def __repr__(self) -> str:
        return f"<HospitalSetting {self.key}={self.value}>"
