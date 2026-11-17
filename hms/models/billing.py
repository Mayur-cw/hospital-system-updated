from datetime import UTC, datetime
from decimal import Decimal

from hms.extensions import db
from hms.models.base import TimestampMixin


class InvoiceStatus:
    DRAFT = 'Draft'
    ISSUED = 'Issued'
    PAID = 'Paid'
    VOID = 'Void'
    REFUNDED = 'Refunded'
    ALL = (DRAFT, ISSUED, PAID, VOID, REFUNDED)

class PaymentMethod:
    CASH = 'Cash'
    CARD = 'Card'
    UPI = 'UPI'
    NET_BANKING = 'NetBanking'
    MOCK = 'Mock'
    ALL = (CASH, CARD, UPI, NET_BANKING, MOCK)

class PaymentStatus:
    PENDING = 'Pending'
    SUCCESS = 'Success'
    FAILED = 'Failed'
    REFUNDED = 'Refunded'
    ALL = (PENDING, SUCCESS, FAILED, REFUNDED)

class Invoice(TimestampMixin, db.Model):
    __tablename__ = 'invoice'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='RESTRICT'), nullable=True, index=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('admission.id', ondelete='RESTRICT'), nullable=True, index=True)

    status = db.Column(db.String(20), default=InvoiceStatus.ISSUED, nullable=False, index=True)
    issued_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    due_at = db.Column(db.DateTime, nullable=True)

    subtotal = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    tax = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    discount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    total = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)

    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('invoices', lazy='dynamic'))
    items = db.relationship('InvoiceItem', backref='invoice', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', cascade='all, delete-orphan')

    # D-11 Composite index
    __table_args__ = (
        db.Index('ix_invoice_patient_status', 'patient_id', 'status'),
    )

    # Legacy compatibility adapters
    bill_id = db.synonym('id')
    user_id = db.synonym('patient_id')
    apt_id = db.synonym('appointment_id')

    def __init__(self, **kwargs):
        import random
        if 'bill_id' in kwargs and 'id' not in kwargs:
            kwargs['id'] = kwargs.pop('bill_id')
        if 'user_id' in kwargs and 'patient_id' not in kwargs:
            kwargs['patient_id'] = kwargs.pop('user_id')
        if 'apt_id' in kwargs and 'appointment_id' not in kwargs:
            kwargs['appointment_id'] = kwargs.pop('apt_id')
        if 'amount' in kwargs:
            amt = Decimal(str(kwargs.pop('amount')))
            kwargs.setdefault('subtotal', amt)
            kwargs.setdefault('total', amt)
        if 'invoice_number' not in kwargs:
            kwargs['invoice_number'] = f"INV-LEGACY-{random.randint(100000, 999999)}"
        super().__init__(**kwargs)

    @property
    def amount(self):
        return self.total

    @amount.setter
    def amount(self, val):
        dec_val = Decimal(str(val))
        self.subtotal = dec_val
        self.total = dec_val

    @property
    def date(self):
        return self.issued_at

    @date.setter
    def date(self, val):
        self.issued_at = val

    def recalculate_totals(self):
        self.subtotal = sum((item.total_price for item in self.items), Decimal('0.00'))
        self.total = max(Decimal('0.00'), self.subtotal + self.tax - self.discount)

    def __repr__(self) -> str:
        return f"<Invoice {self.id}: {self.invoice_number} ({self.status}) Total: ₹{self.total}>"


class InvoiceItem(TimestampMixin, db.Model):
    __tablename__ = 'invoice_item'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id', ondelete='CASCADE'), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)

    def calculate_total(self):
        self.total_price = self.quantity * self.unit_price


class Payment(TimestampMixin, db.Model):
    __tablename__ = 'payment'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id', ondelete='RESTRICT'), nullable=False, index=True)
    method = db.Column(db.String(20), default=PaymentMethod.MOCK, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default=PaymentStatus.SUCCESS, nullable=False)
    gateway_ref = db.Column(db.String(100), nullable=True)
    idempotency_key = db.Column(db.String(64), unique=True, nullable=True, index=True)
    paid_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    recorder = db.relationship('User', foreign_keys=[recorded_by])

    def __repr__(self) -> str:
        return f"<Payment {self.id}: ₹{self.amount} ({self.status}) for Invoice {self.invoice_id}>"
