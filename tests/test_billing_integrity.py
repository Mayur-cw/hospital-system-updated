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


def test_t_pay_003_unpaid_bills_hero_alert_on_patient_dashboard(client_no_csrf, app_no_csrf):
    """
    T-PAY-003: Patient without active room admission who has pending unpaid bills sees
    the prominent hero alert banner with dues, invoice details, and pay actions.
    Once settled, the banner gracefully clears.
    """
    # 1. Login as Patient 1 (p1@test.local has unpaid bill 1 of ₹500.00)
    login_resp = client_no_csrf.post('/login', data={'email': 'p1@test.local', 'password': 'Pass@123'}, follow_redirects=True)
    assert login_resp.status_code == 200

    # 2. Visit dashboard
    dash_resp = client_no_csrf.get('/', follow_redirects=True)
    dash_html = dash_resp.data.decode('utf-8')

    # Verify hero banner shows outstanding dues
    assert "Outstanding Hospital Bill" in dash_html
    assert "Payment Action Required" in dash_html
    assert "Total Amount Due" in dash_html
    assert "500.00" in dash_html
    assert "Pay Earliest Bill" in dash_html
    assert "Pay Now" in dash_html

    # 3. Settle the bill via payment simulation
    with app_no_csrf.app_context():
        p1 = User.query.get(4)
        success, msg, inv = BillingService.process_demo_payment(
            bill_id=1, payment_mode='upi', patient_user=p1, bank_name='GPay'
        )
        assert success is True
        assert inv.status == 'Paid'

    # 4. Refresh patient dashboard; alert banner must no longer be present
    dash_resp2 = client_no_csrf.get('/', follow_redirects=True)
    dash_html2 = dash_resp2.data.decode('utf-8')
    assert "Outstanding Hospital Bill" not in dash_html2
    assert "Payment Action Required" not in dash_html2


def test_t_pay_004_admitted_patient_shows_admission_banner_priority(client_no_csrf, app_no_csrf):
    """
    T-PAY-004: When a patient is actively admitted in a room, the inpatient care banner
    has display priority over the unpaid bills hero.
    """
    from models import Admission, Room
    # Admit patient 1 into Room 101
    with app_no_csrf.app_context():
        adm = Admission(
            apt_id=1,
            patient_id=4,
            doctor_id=1,
            room_id=1,
            status='Admitted',
            tentative_days=3
        )
        Room.query.get(1).status = 'Occupied'
        db.session.add(adm)
        db.session.commit()

    # Login as Patient 1
    client_no_csrf.post('/login', data={'email': 'p1@test.local', 'password': 'Pass@123'}, follow_redirects=True)
    resp = client_no_csrf.get('/', follow_redirects=True)
    html = resp.data.decode('utf-8')

    # Active admission banner must show
    assert "Currently Admitted Inpatient" in html
    assert "Room 101" in html
    # The non-admitted unpaid bills hero must not replace the active room care banner
    assert "Outstanding Hospital Bill" not in html

