# routes/patient.py
import uuid
from datetime import datetime
from decimal import Decimal

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from hms.extensions import db
from hms.models.admission import Admission, AdmissionStatus
from hms.models.appointment import Appointment, AppointmentStatus
from hms.models.billing import Billing, Invoice, PaymentMethod
from hms.models.doctor import Doctor
from hms.models.record import MedicalRecord
from hms.models.user import User
from hms.policies import (
    can_cancel_appointment,
    can_modify_appointment,
    can_record_payment,
    can_view_invoice,
)
from hms.services.appointments import (
    AppointmentCutoffError,
    AppointmentService,
    InvalidStateTransitionError,
    SlotAlreadyBookedError,
)
from hms.services.billing import BillingService

patient_bp = Blueprint('patient', __name__)


# ── UTILITIES & API ──────────────────────────────────────────────────

@patient_bp.route('/get_booked_slots', methods=['POST'])
@login_required
def get_booked_slots():
    """B-10: Typed slot booking check, safe against empty/bad input."""
    data = request.get_json(silent=True) or {}
    req_date = data.get('date')
    target_doctor = data.get('doctor')

    if not req_date or not target_doctor:
        return jsonify([])

    doc_user = User.query.filter_by(username=target_doctor).first()
    if not doc_user:
        return jsonify([])

    doc_profile = Doctor.query.filter_by(user_id=doc_user.id).first()
    if not doc_profile:
        return jsonify([])

    try:
        query_date = datetime.strptime(req_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify([])

    day_start = datetime.combine(query_date, datetime.min.time())
    day_end = datetime.combine(query_date, datetime.max.time())

    booked_apts = Appointment.query.filter(
        Appointment.doctor_id == doc_profile.id,
        Appointment.starts_at >= day_start,
        Appointment.starts_at <= day_end,
        Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.MISSED]),
        Appointment.is_active.is_(True)
    ).all()

    booked_times = [a.starts_at.strftime('%I:%M %p') for a in booked_apts]
    return jsonify(booked_times)


# ── BOOKING WIZARD ───────────────────────────────────────────────────

@patient_bp.route('/patients', methods=['GET', 'POST'])
@login_required
def patient_booking():
    """Book a new outpatient consultation (D-01, D-03, B-11)."""
    raw_doctors = Doctor.query.all()
    doct = [
        {
            'doctorname': d.user.username if d.user else "Physician",
            'dept': d.department.name if d.department else (d.dept or "General Medicine")
        }
        for d in raw_doctors if d.user
    ]

    if request.method == "POST":
        disease = request.form.get('disease', '').strip()
        time = request.form.get('time', '').strip()
        date_str = request.form.get('date', '').strip()
        doctor = request.form.get('doctor', '').strip()

        if not all([disease, time, date_str, doctor]):
            flash("All booking fields are required.", "danger")
            return render_template('bookings/book_appointment.html', doct=doct)

        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(time, '%I:%M %p').time()
            starts_at_dt = datetime.combine(appointment_date, appointment_time)

            now = datetime.now()
            if starts_at_dt < now:
                flash("Cannot schedule an appointment in the past.", "danger")
                return redirect(url_for('patient.patient_booking'))

        except ValueError:
            flash("Invalid date or time format.", "danger")
            return redirect(url_for('patient.patient_booking'))

        # Resolve doctor
        doc_user = User.query.filter_by(username=doctor).first()
        doc_obj = Doctor.query.filter_by(user_id=doc_user.id).first() if doc_user else None
        doc_id = doc_obj.id if doc_obj else 1

        try:
            new_apt = AppointmentService.book(
                patient_id=current_user.id,
                doctor_id=doc_id,
                starts_at=starts_at_dt,
                reason=disease,
                actor=current_user
            )

            # Generate consultation invoice
            fee = doc_obj.consultation_fee if (doc_obj and doc_obj.consultation_fee) else Decimal('500.00')
            BillingService.create_appointment_invoice(new_apt, fee=fee, actor=current_user)

            return redirect(url_for('patient.booking_success', apt_id=new_apt.id))

        except SlotAlreadyBookedError:
            flash("Slot Unavailable: That time slot was just taken. Please choose another.", "warning")
            return redirect(url_for('patient.patient_booking'))
        except Exception as e:
            req_id = getattr(g, 'request_id', 'REQ-ERR')
            current_app.logger.exception("Booking failed: %s [Request-ID: %s]", e, req_id)
            flash(f"Booking could not be completed. Please try again. (Reference: {req_id})", "danger")
            return redirect(url_for('patient.patient_booking'))

    pre_dept = request.args.get('dept', '')
    pre_doc = request.args.get('doctor', '')

    return render_template('bookings/book_appointment.html', doct=doct, pre_dept=pre_dept, pre_doc=pre_doc)


@patient_bp.route('/booking_success/<int:apt_id>')
@login_required
def booking_success(apt_id):
    appointment = db.session.get(Appointment, apt_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('main.index'))

    if current_user.usertype != "Doctor" and appointment.patient_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('main.index'))

    return render_template('bookings/booking_success.html', appointment=appointment)


# ── RESCHEDULE & CANCEL ──────────────────────────────────────────────

@patient_bp.route('/reschedule/<int:apt_id>', methods=['GET', 'POST'])
@patient_bp.route('/edit/<int:apt_id>', methods=['GET', 'POST'])
@login_required
def reschedule_appointment(apt_id):
    """B-05 & F-01: Reschedule an existing scheduled appointment."""
    appointment = db.session.get(Appointment, apt_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('patient.dashboard'))

    if not can_modify_appointment(current_user, appointment):
        abort(403)

    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        time_str = request.form.get('time', '').strip()
        reason = request.form.get('disease', '').strip()

        if not date_str or not time_str:
            flash("Please select both a valid date and time slot.", "warning")
            return redirect(url_for('patient.reschedule_appointment', apt_id=apt_id))

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            target_time = datetime.strptime(time_str, '%I:%M %p').time()
            new_starts_at = datetime.combine(target_date, target_time)

            if new_starts_at < datetime.now():
                flash("Cannot reschedule an appointment to a past time.", "danger")
                return redirect(url_for('patient.reschedule_appointment', apt_id=apt_id))

            AppointmentService.reschedule(
                appointment_id=appointment.id,
                new_starts_at=new_starts_at,
                actor=current_user,
                reason=reason
            )
            flash("Appointment successfully rescheduled!", "success")
            return redirect(url_for('patient.dashboard'))

        except SlotAlreadyBookedError:
            flash("That slot was just booked by another patient. Please pick another slot.", "warning")
            return redirect(url_for('patient.reschedule_appointment', apt_id=apt_id))
        except AppointmentCutoffError as e:
            flash(str(e), "warning")
            return redirect(url_for('patient.dashboard'))
        except InvalidStateTransitionError as e:
            flash(str(e), "danger")
            return redirect(url_for('patient.dashboard'))
        except Exception as e:
            flash(f"Reschedule failed: {e}", "danger")
            return redirect(url_for('patient.reschedule_appointment', apt_id=apt_id))

    raw_doctors = Doctor.query.all()
    doct = [
        {
            'doctorname': d.user.username if d.user else "Physician",
            'dept': d.department.name if d.department else (d.dept or "General Medicine")
        }
        for d in raw_doctors if d.user
    ]
    return render_template('bookings/edit.html', posts=appointment, doct=doct)


@patient_bp.route('/cancel/<int:apt_id>', methods=['POST'])
@login_required
def cancel_appointment(apt_id):
    """B-17: Cancel appointment with state machine guard."""
    appointment = db.session.get(Appointment, apt_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('patient.dashboard'))

    if not can_cancel_appointment(current_user, appointment):
        abort(403)

    try:
        AppointmentService.cancel(apt_id, actor=current_user, reason="Cancelled by patient")
        flash("Appointment successfully cancelled.", "info")
    except InvalidStateTransitionError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Cancellation error: {e}", "danger")

    return redirect(url_for('patient.dashboard'))


# ── DASHBOARDS & HISTORY ─────────────────────────────────────────────

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    """Patient appointments hub with relational queries and B-20 N+1 prevention."""
    active_admission = None
    if current_user.usertype == "Doctor":
        doc_profile = Doctor.query.filter_by(user_id=current_user.id).first()
        query = Appointment.query.filter(
            Appointment.doctor_id == doc_profile.id
        ).order_by(Appointment.starts_at.desc()).all() if doc_profile else []
    else:
        query = Appointment.query.filter(
            Appointment.patient_id == current_user.id
        ).order_by(Appointment.starts_at.desc()).all()
        active_admission = Admission.query.filter_by(
            patient_id=current_user.id,
            status=AdmissionStatus.ADMITTED
        ).first()

    # B-20: Fetch only prescribed IDs for this specific query set
    if query:
        apt_ids = [a.id for a in query]
        prescribed_query = db.session.query(MedicalRecord.appointment_id).filter(
            MedicalRecord.appointment_id.in_(apt_ids)
        ).all()
        prescribed_apt_ids = {r[0] for r in prescribed_query}
    else:
        prescribed_apt_ids = set()

    return render_template(
        'bookings/appointment_history.html',
        query=query,
        page_title="Appointment Log",
        prescribed_apt_ids=prescribed_apt_ids,
        active_admission=active_admission
    )


@patient_bp.route('/upcoming_bookings')
@login_required
def upcoming_bookings():
    """Upcoming appointments filtered directly via SQL (B-08, B-09, B-20)."""
    now = datetime.now()
    active_admission = None

    if current_user.usertype == "Doctor":
        doc_profile = Doctor.query.filter_by(user_id=current_user.id).first()
        upcoming_list = Appointment.query.filter(
            Appointment.doctor_id == doc_profile.id,
            Appointment.starts_at >= now,
            Appointment.status == AppointmentStatus.SCHEDULED
        ).order_by(Appointment.starts_at.asc()).all() if doc_profile else []
    else:
        upcoming_list = Appointment.query.filter(
            Appointment.patient_id == current_user.id,
            Appointment.starts_at >= now,
            Appointment.status == AppointmentStatus.SCHEDULED
        ).order_by(Appointment.starts_at.asc()).all()
        active_admission = Admission.query.filter_by(
            patient_id=current_user.id,
            status=AdmissionStatus.ADMITTED
        ).first()

    return render_template(
        'bookings/appointment_history.html',
        query=upcoming_list,
        page_title="Upcoming Appointments",
        prescribed_apt_ids=set(),
        active_admission=active_admission
    )


@patient_bp.route('/past_records')
@login_required
def past_records():
    """Clinical history filtered directly via SQL (B-20)."""
    now = datetime.now()
    active_admission = None

    if current_user.usertype == "Doctor":
        doc_profile = Doctor.query.filter_by(user_id=current_user.id).first()
        query = Appointment.query.filter(
            Appointment.doctor_id == doc_profile.id,
            db.or_(
                Appointment.status.in_([AppointmentStatus.COMPLETED, AppointmentStatus.MISSED, 'Attended']),
                Appointment.starts_at < now
            )
        ).order_by(Appointment.starts_at.desc()).all() if doc_profile else []
    else:
        query = Appointment.query.filter(
            Appointment.patient_id == current_user.id,
            db.or_(
                Appointment.status.in_([AppointmentStatus.COMPLETED, AppointmentStatus.MISSED, 'Attended']),
                Appointment.starts_at < now
            )
        ).order_by(Appointment.starts_at.desc()).all()
        active_admission = Admission.query.filter_by(
            patient_id=current_user.id,
            status=AdmissionStatus.ADMITTED
        ).first()

    if query:
        apt_ids = [a.id for a in query]
        prescribed_query = db.session.query(MedicalRecord.appointment_id).filter(
            MedicalRecord.appointment_id.in_(apt_ids)
        ).all()
        prescribed_apt_ids = {r[0] for r in prescribed_query}
    else:
        prescribed_apt_ids = set()

    return render_template(
        'bookings/appointment_history.html',
        query=query,
        page_title="Patient History",
        is_past_record=True,
        prescribed_apt_ids=prescribed_apt_ids,
        active_admission=active_admission
    )


# ── BILLING & PAYMENT GATEWAY ────────────────────────────────────────

@patient_bp.route('/my_bills')
@login_required
def my_bills():
    """Patient view of their issued invoices."""
    if current_user.usertype != 'Patient':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('main.index'))

    my_invoices = Billing.query.filter_by(user_id=current_user.id).order_by(Billing.issued_on.desc()).all()
    return render_template('bookings/my_bills.html', invoices=my_invoices)


@patient_bp.route('/bills/<int:bill_id>/invoice')
@login_required
def view_invoice(bill_id):
    """View invoice with payment checkout options."""
    invoice = db.session.get(Invoice, bill_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('patient.my_bills'))

    if not can_view_invoice(current_user, invoice):
        abort(403)

    if invoice.status == 'Paid':
        return redirect(url_for('patient.view_receipt', bill_id=bill_id))

    return render_template('bookings/pay_invoice.html', invoice=invoice)


@patient_bp.route('/bills/<int:bill_id>/pay', methods=['POST'])
@login_required
def process_payment(bill_id):
    """
    Process payment against an invoice (B-18, F-06).
    Rejects unauthorized cash payment self-marking.
    Enforces idempotency and records real payment transaction.
    """
    invoice = db.session.get(Invoice, bill_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('patient.my_bills'))

    if not can_view_invoice(current_user, invoice):
        abort(403)

    if invoice.status == 'Paid':
        flash("This invoice is already settled.", "info")
        return redirect(url_for('patient.view_receipt', bill_id=bill_id))

    payment_mode = (request.form.get('payment_mode') or '').strip().lower()

    if not payment_mode:
        flash("Please select a payment method.", "warning")
        return redirect(url_for('patient.view_invoice', bill_id=bill_id))

    # B-18: Reject self-marking as cash paid by patient
    if payment_mode == 'cash' and not can_record_payment(current_user):
        flash("Cash payments cannot be self-processed online. Please present your invoice at the hospital billing cashier desk.", "warning")
        return redirect(url_for('patient.view_invoice', bill_id=bill_id))

    allowed_modes = {
        'netbanking': PaymentMethod.NET_BANKING,
        'upi': PaymentMethod.UPI,
        'card': PaymentMethod.CARD,
        'mock': PaymentMethod.MOCK,
        'cash': PaymentMethod.CASH
    }

    method = allowed_modes.get(payment_mode, PaymentMethod.MOCK)
    idempotency_key = request.form.get('idempotency_key') or f"PAY-{invoice.id}-{uuid.uuid4().hex[:12]}"

    try:
        BillingService.record_payment(
            invoice_id=invoice.id,
            amount=invoice.total,
            method=method,
            gateway_ref=f"GW-{uuid.uuid4().hex[:8].upper()}",
            idempotency_key=idempotency_key,
            actor=current_user
        )
        flash("Transaction successful! Your official receipt is ready.", "success")
        return redirect(url_for('patient.view_receipt', bill_id=bill_id))
    except Exception as e:
        req_id = getattr(g, 'request_id', 'PAY-ERR')
        current_app.logger.exception("Payment failed: %s [Req: %s]", e, req_id)
        flash(f"Payment processing failed. (Reference: {req_id})", "danger")
        return redirect(url_for('patient.view_invoice', bill_id=bill_id))


@patient_bp.route('/bills/<int:bill_id>/receipt')
@login_required
def view_receipt(bill_id):
    """View official payment receipt."""
    invoice = db.session.get(Invoice, bill_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('patient.my_bills'))

    if not can_view_invoice(current_user, invoice):
        abort(403)

    if invoice.status != 'Paid':
        flash('This invoice has not been settled yet.', 'warning')
        return redirect(url_for('patient.view_invoice', bill_id=bill_id))

    return render_template('bookings/receipt.html', invoice=invoice)
