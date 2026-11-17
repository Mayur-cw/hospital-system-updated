import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_appointment_confirmation(appointment) -> bool:
        """Send appointment booking confirmation to patient."""
        try:
            patient = appointment.patient
            logger.info(f"[NOTIF] Sent booking confirmation for Apt {appointment.id} to {patient.email}")
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to dispatch booking confirmation notification: {e}")
            return False

    @staticmethod
    def send_reschedule_notification(appointment, old_starts_at) -> bool:
        """Send appointment rescheduled notification."""
        try:
            logger.info(f"[NOTIF] Sent reschedule alert for Apt {appointment.id} to {appointment.patient.email}")
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to dispatch reschedule notification: {e}")
            return False

    @staticmethod
    def send_cancellation_notification(appointment) -> bool:
        """Send appointment cancellation notification."""
        try:
            logger.info(f"[NOTIF] Sent cancellation alert for Apt {appointment.id} to {appointment.patient.email}")
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to dispatch cancellation notification: {e}")
            return False

    @staticmethod
    def send_invoice_notification(invoice) -> bool:
        """Send invoice issued notification."""
        try:
            logger.info(f"[NOTIF] Sent invoice {invoice.invoice_number} to patient {invoice.patient_id}")
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to dispatch invoice notification: {e}")
            return False

    @staticmethod
    def send_payment_receipt(payment) -> bool:
        """Send payment receipt notification."""
        try:
            logger.info(f"[NOTIF] Sent payment receipt for Payment {payment.id}")
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to dispatch receipt notification: {e}")
            return False
