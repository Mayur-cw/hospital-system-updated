import pytest
from decimal import Decimal
from models import db, Billing, User
from services.billing import BillingService

def test_t_pay_001_simulated_payment_in_demo_mode_tags_mock(app_no_csrf):
    """
    T-PAY-001: Submitting simulated payment in DEMO_ONLY mode clearly tags the
    settlement as demo_simulation rather than claiming a real banking transaction.
    """
    with app_no_csrf.app_context():
        p1 = User.query.get(4)
        invoice = Billing.query.get(1)
        assert invoice.status == 'Unpaid'

        # Execute demo simulation
        success, msg, updated = BillingService.process_demo_payment(
            bill_id=1,
            payment_mode='netbanking',
            patient_user=p1,
            bank_name='SBI'
        )
        assert success is True
        assert "Simulation Successful" in msg
        assert "demo_simulation" in updated.payment_mode
        assert updated.bank_name == 'SBI'
        assert "DEMO-MOCK" in updated.transaction_ref

def test_t_pay_002_cashier_settlement_creates_audited_settlement(app_no_csrf):
    """
    T-PAY-002: Authorized cashier counter payment records verified cash settlement
    with cashier attribution and transaction reference.
    """
    with app_no_csrf.app_context():
        cashier = User.query.get(6)
        invoice = Billing.query.get(2)
        assert invoice.status == 'Unpaid'

        success, msg, updated = BillingService.settle_cashier_payment(
            bill_id=2,
            payment_mode='cash',
            cashier_user=cashier,
            transaction_ref='CASH-DRAWER-01-TXN-42'
        )
        assert success is True
        assert updated.status == 'Paid'
        assert updated.payment_mode == 'cash'
        assert updated.transaction_ref == 'CASH-DRAWER-01-TXN-42'
        assert updated.settled_by == 'Cashier User'
