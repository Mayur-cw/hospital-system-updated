from datetime import UTC, datetime

from hms.extensions import db


class TimestampMixin:
    """Provides created_at and updated_at UTC timestamps."""
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

class SoftDeleteMixin:
    """Provides soft-delete capabilities."""
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def soft_delete(self):
        self.is_active = False
        self.deleted_at = datetime.now(UTC)

    def restore(self):
        self.is_active = True
        self.deleted_at = None
