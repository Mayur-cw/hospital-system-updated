import logging

from flask import g, has_request_context, request

from hms.extensions import db
from hms.models.audit import AuditEvent

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def record(action: str, entity_type: str, entity_id=None, actor=None,
               before=None, after=None, ip: str | None = None, user_agent: str | None = None,
               request_id: str | None = None) -> AuditEvent | None:
        """Write an append-only audit event."""
        try:
            actor_id = None
            actor_role = None

            if actor:
                actor_id = getattr(actor, 'id', None)
                actor_role = getattr(actor, 'usertype', None)

            if has_request_context():
                if not ip:
                    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                    if ip and ',' in ip:
                        ip = ip.split(',')[0].strip()
                if not user_agent:
                    user_agent = request.headers.get('User-Agent', '')[:255]
                if not request_id and hasattr(g, 'request_id'):
                    request_id = g.request_id

            event = AuditEvent(
                actor_id=actor_id,
                actor_role=actor_role,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                before_state=before,
                after_state=after,
                ip_address=ip,
                user_agent=user_agent,
                request_id=request_id
            )
            db.session.add(event)
            # Flush to database so it gets an ID and is part of the transaction
            db.session.flush()
            return event
        except Exception:
            logger.exception("Failed to record audit event (%s on %s)", action, entity_type)
            return None
