from datetime import datetime
from models import db, Billing, AuditLog
from config import Config

class BillingService:
    @staticmethod
    def settle_cashier_payment(bill_id, payment_mode, cashier_user, transaction_ref=None):
        """
        Record an authorized, verified payment settled at the hospital cashier counter.
        """
        invoice = Billing.query.get(bill_id)
        if not invoice:
            return False, "Invoice not found.", None

        if invoice.status == 'Paid':
            return False, "This invoice is already settled.", invoice

        now = datetime.now()
        invoice.status = 'Paid'
        invoice.paid_on = now
        invoice.payment_mode = payment_mode
        invoice.transaction_ref = transaction_ref or f"CASH-{now.strftime('%Y%m%d%H%M%S')}"
        invoice.settled_by = cashier_user.username

        audit = AuditLog(
            apt_id=invoice.apt_id,
            user_id=cashier_user.id,
            action=f"PAYMENT SETTLED ({payment_mode.upper()} Rs.{invoice.amount} by {cashier_user.username})",
            timestamp=now.strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(audit)
        db.session.commit()

        return True, f"Payment of Rs.{invoice.amount} confirmed and settled successfully.", invoice

    @staticmethod
    def process_demo_payment(bill_id, payment_mode, patient_user, bank_name=None):
        """
        Processes simulated patient payment in DEMO_ONLY mode.
        Enforces clear disclaimer and prevents false production payment claims.
        """
        invoice = Billing.query.get(bill_id)
        if not invoice:
            return False, "Invoice not found.", None

        if not Config.DEMO_ONLY:
            return False, "Online payment gateway is not configured for live production. Please settle at the hospital cashier.", None

        now = datetime.now()
        invoice.status = 'Paid'
        invoice.paid_on = now
        invoice.payment_mode = f"demo_simulation_{payment_mode}"
        invoice.bank_name = bank_name if payment_mode == 'netbanking' else None
        invoice.transaction_ref = f"DEMO-MOCK-{now.strftime('%Y%m%d%H%M%S')}"
        invoice.settled_by = f"Patient {patient_user.username} (Simulation)"

        audit = AuditLog(
            apt_id=invoice.apt_id,
            user_id=patient_user.id,
            action=f"DEMO PAYMENT SIMULATED ({payment_mode} Rs.{invoice.amount})",
            timestamp=now.strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(audit)
        db.session.commit()

        return True, "Simulation Successful: Invoice marked paid for demonstration purposes. (No real funds transferred).", invoice
