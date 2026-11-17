from datetime import UTC, datetime

from hms.extensions import db


class AuditEvent(db.Model):
    __tablename__ = 'audit_event'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    actor_role = db.Column(db.String(50), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=False, index=True)
    entity_id = db.Column(db.String(50), nullable=True, index=True)

    before_state = db.Column(db.JSON, nullable=True)
    after_state = db.Column(db.JSON, nullable=True)

    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    request_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)

    actor = db.relationship('User', foreign_keys=[actor_id])

    # Legacy compatibility synonyms
    tid = db.synonym('id')
    user_id = db.synonym('actor_id')
    timestamp = db.synonym('created_at')

    @property
    def pid(self) -> str:
        return str(self.entity_id or (self.actor.id if self.actor else ''))

    @property
    def email(self) -> str:
        return self.actor.email if self.actor else 'system@hospital.internal'

    @property
    def name(self) -> str:
        return self.actor.username if self.actor else (self.actor_role or 'System')

    # D-11 Composite index
    __table_args__ = (
        db.Index('ix_audit_entity_created', 'entity_type', 'entity_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<AuditEvent {self.id}: {self.action} on {self.entity_type} {self.entity_id} by {self.actor_id}>"


# Legacy synonym
AuditLog = AuditEvent
