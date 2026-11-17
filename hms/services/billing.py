import math
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from hms.extensions import db
from hms.models.admission import Admission
from hms.models.appointment import Appointment
from hms.models.billing import (
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from hms.services.audit import AuditService
from hms.services.notifications import NotificationService


class BillingError(Exception):
    pass

class InvoiceNotFoundError(BillingError):
    pass

class PaymentProcessingError(BillingError):
    pass

class BillingService:
    @staticmethod
    def _generate_invoice_number() -> str:
        """Generate unique invoice number in format INV-YYYY-XXXXXX."""
        year = datetime.now().year
        # Generate with sequence or random high-entropy token
        for _ in range(10):
            seq = random.randint(100000, 999999)
            candidate = f"INV-{year}-{seq}"
            if not Invoice.query.filter_by(invoice_number=candidate).first():
                return candidate
        raise BillingError("Could not generate a unique invoice number.")

    @staticmethod
    def create_appointment_invoice(appointment: Appointment,
                                   fee: Decimal | None = None,
                                   actor=None) -> Invoice:
        """Create an itemized consultation invoice for an appointment."""
        if fee is None:
            if appointment.doctor_rel and appointment.doctor_rel.consultation_fee:
                fee = appointment.doctor_rel.consultation_fee
            else:
                fee = Decimal('500.00')
        else:
            fee = Decimal(str(fee))

        doc_name = appointment.doctor_rel.user.username if appointment.doctor_rel and appointment.doctor_rel.user else "Physician"

        invoice = Invoice(
            invoice_number=BillingService._generate_invoice_number(),
            patient_id=appointment.patient_id,
            appointment_id=appointment.id,
            status=InvoiceStatus.ISSUED,
            subtotal=fee,
            total=fee,
            issued_at=datetime.now(UTC),
            due_at=datetime.now(UTC) + timedelta(days=7)
        )
        db.session.add(invoice)
        db.session.flush()

        item = InvoiceItem(
            invoice_id=invoice.id,
            description=f"Consultation Fee — Dr. {doc_name}",
            quantity=1,
            unit_price=fee,
            total_price=fee
        )
        db.session.add(item)
        db.session.commit()

        AuditService.record(
            action='INVOICE_GENERATED',
            entity_type='Invoice',
            entity_id=invoice.id,
            actor=actor or appointment.patient,
            after={
                'invoice_number': invoice.invoice_number,
                'total': str(invoice.total),
                'appointment_id': appointment.id
            }
        )
        NotificationService.send_invoice_notification(invoice)
        return invoice

    @staticmethod
    def create_inpatient_invoice(admission: Admission, actor=None) -> Invoice:
        """Generate final settlement invoice upon inpatient discharge."""
        now = datetime.now(UTC)
        adm_date = admission.admission_date
        if adm_date.tzinfo is None:
            adm_date = adm_date.replace(tzinfo=UTC)

        # Calculate started 24-hour blocks (minimum 1 day) - resolves B-07
        total_seconds = max(0.0, (now - adm_date).total_seconds())
        days = max(1, math.ceil(total_seconds / 86400.0))

        room = admission.room
        rate = room.rate_per_day if room and room.rate_per_day else Decimal('1000.00')
        room_total = days * rate

        invoice = Invoice(
            invoice_number=BillingService._generate_invoice_number(),
            patient_id=admission.patient_id,
            appointment_id=admission.appointment_id,
            admission_id=admission.id,
            status=InvoiceStatus.ISSUED,
            subtotal=room_total,
            total=room_total,
            issued_at=now,
            due_at=now + timedelta(days=3)
        )
        db.session.add(invoice)
        db.session.flush()

        item = InvoiceItem(
            invoice_id=invoice.id,
            description=f"Room Rent ({days} days @ ₹{rate}/day) — Room {room.room_number if room else ''} ({room.ward_type if room else ''})",
            quantity=days,
            unit_price=rate,
            total_price=room_total
        )
        db.session.add(item)
        db.session.commit()

        AuditService.record(
            action='INPATIENT_INVOICE_GENERATED',
            entity_type='Invoice',
            entity_id=invoice.id,
            actor=actor,
            after={
                'invoice_number': invoice.invoice_number,
                'days': days,
                'total': str(invoice.total),
                'admission_id': admission.id
            }
        )
        NotificationService.send_invoice_notification(invoice)
        return invoice

    @staticmethod
    def record_payment(invoice_id: int, amount: Decimal, method: str = PaymentMethod.MOCK,
                       gateway_ref: str | None = None, idempotency_key: str | None = None,
                       actor=None) -> Payment:
        """
        Record a payment against an invoice (F-06).
        Protects against double-charge using unique idempotency key.
        """
        amount = Decimal(str(amount))

        # Check idempotency key if provided
        if idempotency_key:
            existing_payment = Payment.query.filter_by(idempotency_key=idempotency_key).first()
            if existing_payment:
                return existing_payment

        invoice = db.session.get(Invoice, invoice_id)
        if not invoice:
            raise InvoiceNotFoundError("Invoice not found.")

        payment = Payment(
            invoice_id=invoice.id,
            method=method,
            amount=amount,
            status=PaymentStatus.SUCCESS,
            gateway_ref=gateway_ref,
            idempotency_key=idempotency_key,
            paid_at=datetime.now(UTC),
            recorded_by=getattr(actor, 'id', None)
        )
        db.session.add(payment)

        # Check total payments recorded
        db.session.flush()
        total_paid = sum((p.amount for p in invoice.payments if p.status == PaymentStatus.SUCCESS), Decimal('0.00'))
        if total_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if idempotency_key:
                existing = Payment.query.filter_by(idempotency_key=idempotency_key).first()
                if existing:
                    return existing
            raise

        AuditService.record(
            action='PAYMENT_RECORDED',
            entity_type='Payment',
            entity_id=payment.id,
            actor=actor,
            after={
                'invoice_id': invoice.id,
                'amount': str(payment.amount),
                'method': payment.method,
                'invoice_status': invoice.status
            }
        )
        NotificationService.send_payment_receipt(payment)
        return payment
