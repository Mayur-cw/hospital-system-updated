from datetime import UTC, datetime

from hms.extensions import db
from hms.models.base import TimestampMixin


class NotificationStatus:
    PENDING = 'Pending'
    SENT = 'Sent'
    FAILED = 'Failed'
    ALL = (PENDING, SENT, FAILED)


class NotificationOutbox(TimestampMixin, db.Model):
    __tablename__ = 'notification_outbox'

    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(120), nullable=False, index=True)
    channel = db.Column(db.String(20), default='email', nullable=False)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default=NotificationStatus.PENDING, nullable=False, index=True)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)

    def mark_sent(self):
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now(UTC)
        self.attempts += 1

    def mark_failed(self, error: str):
        self.status = NotificationStatus.FAILED
        self.error_message = str(error)
        self.attempts += 1

    def __repr__(self) -> str:
        return f"<NotificationOutbox {self.id}: {self.event_type} to {self.recipient} ({self.status})>"


class InAppNotification(TimestampMixin, db.Model):
    __tablename__ = 'in_app_notification'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='system', nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('in_app_notifications', lazy='dynamic', cascade='all, delete-orphan'))

    def mark_as_read(self):
        self.is_read = True
        self.read_at = datetime.now(UTC)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'category': self.category,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f"<InAppNotification {self.id} for User {self.user_id}: {self.title}>"
