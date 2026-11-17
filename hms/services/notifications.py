import logging
from datetime import datetime

from hms.extensions import db
from hms.models.notification import InAppNotification, NotificationOutbox

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def queue_outbox(recipient: str, event_type: str, subject: str, body: str, channel: str = 'email') -> NotificationOutbox:
        """Queue an outbound notification to the outbox table (F-05)."""
        outbox_entry = NotificationOutbox(
            recipient=recipient,
            channel=channel,
            event_type=event_type,
            subject=subject,
            body=body
        )
        db.session.add(outbox_entry)
        try:
            db.session.commit()
            logger.info(f"[OUTBOX] Queued {event_type} for {recipient}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to queue outbox notification: {e}")
        return outbox_entry

    @staticmethod
    def send_in_app(user_id: int, title: str, message: str, category: str = 'system', link: str | None = None) -> InAppNotification:
        """Create an in-app notification for a user (F-05)."""
        notif = InAppNotification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            link=link
        )
        db.session.add(notif)
        try:
            db.session.commit()
            logger.info(f"[IN-APP] Notification created for user {user_id}: {title}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create in-app notification: {e}")
        return notif

    @classmethod
    def send_appointment_confirmation(cls, appointment) -> bool:
        """Send appointment booking confirmation via outbox and in-app."""
        try:
            patient = appointment.patient
            starts_fmt = appointment.starts_at.strftime('%B %d, %Y at %I:%M %p')
            doc_name = appointment.doctor_rel.user.username if getattr(appointment, 'doctor_rel', None) and appointment.doctor_rel.user else str(getattr(appointment, 'doctor', 'Physician'))
            subject = f"Appointment Confirmed - Hedgewar Hospital Care (#{appointment.id})"
            body = (
                f"Dear {patient.username},\n\n"
                f"Your appointment with Dr. {doc_name} "
                f"has been confirmed for {starts_fmt}.\n\n"
                f"Reason for visit: {appointment.reason or 'Consultation'}\n\n"
                f"Hospital: Hedgewar Hospital Care\n"
                f"Helpline: +91 98500 64866"
            )
            cls.queue_outbox(recipient=patient.email, event_type='booking_confirmation', subject=subject, body=body)

            cls.send_in_app(
                user_id=patient.id,
                title="Appointment Confirmed",
                message=f"Consultation scheduled for {starts_fmt}.",
                category="appointment",
                link="/my_appointments"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to dispatch booking confirmation notification: {e}")
            return False

    @classmethod
    def send_reschedule_notification(cls, appointment, old_starts_at: datetime) -> bool:
        """Send appointment rescheduled notification."""
        try:
            patient = appointment.patient
            new_fmt = appointment.starts_at.strftime('%B %d, %Y at %I:%M %p')
            old_fmt = old_starts_at.strftime('%B %d, %Y at %I:%M %p') if old_starts_at else 'previous time'
            doc_name = appointment.doctor_rel.user.username if getattr(appointment, 'doctor_rel', None) and appointment.doctor_rel.user else str(getattr(appointment, 'doctor', 'Physician'))

            subject = f"Appointment Rescheduled - Hedgewar Hospital Care (#{appointment.id})"
            body = (
                f"Dear {patient.username},\n\n"
                f"Your appointment with Dr. {doc_name} "
                f"has been rescheduled from {old_fmt} to {new_fmt}.\n\n"
                f"Reason: {appointment.reason or 'Rescheduled by request'}"
            )
            cls.queue_outbox(recipient=patient.email, event_type='reschedule', subject=subject, body=body)

            cls.send_in_app(
                user_id=patient.id,
                title="Appointment Rescheduled",
                message=f"Your visit was moved to {new_fmt}.",
                category="appointment",
                link="/my_appointments"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to dispatch reschedule notification: {e}")
            return False

    @classmethod
    def send_cancellation_notification(cls, appointment, actor=None, reason: str | None = None) -> bool:
        """Send appointment cancellation notification."""
        try:
            patient = appointment.patient
            subject = f"Appointment Cancelled - Hedgewar Hospital Care (#{appointment.id})"
            body = (
                f"Dear {patient.username},\n\n"
                f"Your appointment scheduled for {appointment.starts_at.strftime('%B %d, %Y at %I:%M %p')} "
                f"has been cancelled.\n\n"
                f"Reason: {reason or 'Patient / Clinic Request'}"
            )
            cls.queue_outbox(recipient=patient.email, event_type='cancel', subject=subject, body=body)

            cls.send_in_app(
                user_id=patient.id,
                title="Appointment Cancelled",
                message=f"Appointment #{appointment.id} was cancelled.",
                category="appointment",
                link="/my_appointments"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to dispatch cancellation notification: {e}")
            return False

    @classmethod
    def send_invoice_notification(cls, invoice) -> bool:
        """Send invoice issued notification."""
        try:
            patient = invoice.patient
            subject = f"Invoice Issued - #{invoice.invoice_number} | Hedgewar Hospital Care"
            body = (
                f"Dear {patient.username},\n\n"
                f"Invoice #{invoice.invoice_number} has been generated for ₹{invoice.total}.\n"
                f"Status: {invoice.status}\n\n"
                f"You may review and settle your invoice through your patient portal."
            )
            cls.queue_outbox(recipient=patient.email, event_type='invoice_issued', subject=subject, body=body)

            cls.send_in_app(
                user_id=patient.id,
                title="Invoice Issued",
                message=f"Invoice #{invoice.invoice_number} for ₹{invoice.total} is ready.",
                category="billing",
                link="/my_bills"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to dispatch invoice notification: {e}")
            return False

    @classmethod
    def send_payment_receipt(cls, payment) -> bool:
        """Send payment receipt notification."""
        try:
            invoice = payment.invoice
            patient = invoice.patient
            subject = f"Payment Receipt - Invoice #{invoice.invoice_number}"
            body = (
                f"Dear {patient.username},\n\n"
                f"We received your payment of ₹{payment.amount} via {payment.method} on {payment.paid_at.strftime('%B %d, %Y')}.\n"
                f"Status: Settled (Receipt Ref: #{payment.id})"
            )
            cls.queue_outbox(recipient=patient.email, event_type='receipt', subject=subject, body=body)

            cls.send_in_app(
                user_id=patient.id,
                title="Payment Received",
                message=f"Payment of ₹{payment.amount} settled successfully.",
                category="billing",
                link=f"/receipt/{invoice.id}"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to dispatch receipt notification: {e}")
            return False

    @staticmethod
    def get_unread_notifications(user_id: int):
        """Retrieve unread in-app notifications for user."""
        return InAppNotification.query.filter_by(user_id=user_id, is_read=False).order_by(InAppNotification.created_at.desc()).all()

    @staticmethod
    def mark_notification_as_read(notification_id: int, user_id: int) -> bool:
        """Mark single in-app notification as read."""
        notif = InAppNotification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notif:
            notif.mark_as_read()
            db.session.commit()
            return True
        return False
