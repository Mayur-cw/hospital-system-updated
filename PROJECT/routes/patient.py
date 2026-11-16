# routes/patient.py
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from models import db, Appointments, Doctors, MedicalRecord, Billing, Admission
from services.scheduling import SchedulingService
from services.billing import BillingService
from authorization import can_access_invoice

patient_bp = Blueprint('patient', __name__)

# ── UTILITIES ────────────────────────────────────────────────────────

@patient_bp.route('/get_booked_slots', methods=['GET', 'POST'])
def get_booked_slots():
    """Return booked time slots for a given doctor and date to prevent booking collisions."""
    if request.method == 'GET':
        req_date = request.args.get('date', '').strip()
        req_doctor = request.args.get('doctor', '').strip()
        current_apt_id = request.args.get('current_pid')
    else:
        data = request.get_json(silent=True) or request.form or {}
        req_date = data.get('date', '').strip() if data.get('date') else ''
        req_doctor = data.get('doctor', '').strip() if data.get('doctor') else ''
        current_apt_id = data.get('current_pid')

    if not req_date or not req_doctor:
        return jsonify({'booked_times': []})

    query = Appointments.query.filter_by(date=req_date, doctor=req_doctor)
    if current_apt_id:
        try:
            current_apt_id = int(current_apt_id)
            query = query.filter(Appointments.apt_id != current_apt_id)
        except (ValueError, TypeError):
            pass

    bookings = query.all()
    booked_times = [b.time for b in bookings if b.slot not in ['Cancelled', 'Missed']]
    return jsonify({'booked_times': booked_times})


# ── APPOINTMENT BOOKING ──────────────────────────────────────────────

@patient_bp.route('/patients', methods=['POST', 'GET'])
@login_required
def patient_booking():
    raw_doctors = Doctors.query.all()
    doct = [{'doctorname': d.user_account.username, 'dept': d.dept} for d in raw_doctors]

    if request.method == "POST":
        slot     = request.form.get('slot', 'Scheduled').strip()
        disease  = request.form.get('disease', '').strip()
        time     = request.form.get('time', '').strip()
        date_str = request.form.get('date', '').strip()
        dept     = request.form.get('dept', '').strip()
        doctor   = request.form.get('doctor', '').strip()

        if not all([disease, time, date_str, dept, doctor]):
            flash("All appointment details are required.", "danger")
            return render_template('bookings/book_appointment.html', doct=doct)

        # Call concurrency-safe SchedulingService
        success, message, new_apt = SchedulingService.book_appointment(
            user_id=current_user.id,
            doctor_name=doctor,
            dept=dept,
            date_str=date_str,
            time_str=time,
            disease=disease,
            slot=slot
        )

        if success and new_apt:
            flash(f"Appointment booked! Token #{new_apt.token_number} assigned.", "success")
            return redirect(url_for('patient.booking_success', apt_id=new_apt.apt_id))
        else:
            flash(message, "warning")
            return redirect(url_for('patient.patient_booking'))

    pre_dept = request.args.get('dept', '')
    pre_doc = request.args.get('doctor', '')

    return render_template('bookings/book_appointment.html', doct=doct, pre_dept=pre_dept, pre_doc=pre_doc)

@patient_bp.route('/booking_success/<int:apt_id>')
@login_required
def booking_success(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    # Fixed F-17: Only authorized patient, assigned doctor, or admin/receptionist can view
    if current_user.usertype not in ('Admin', 'Receptionist'):
        if current_user.usertype == 'Doctor' and appointment.doctor.lower() != current_user.username.lower():
            flash("Unauthorized access to booking details.", "danger")
            return redirect(url_for('main.index'))
        elif current_user.usertype == 'Patient' and appointment.user_id != current_user.id:
            flash("Unauthorized access to booking details.", "danger")
            return redirect(url_for('main.index'))

    return render_template('bookings/booking_success.html', appointment=appointment)


# ── DASHBOARDS & HISTORY ─────────────────────────────────────────────

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    active_admission = None
    if current_user.usertype == "Doctor":
        query = Appointments.query.filter_by(doctor=current_user.username).all()
    else:
        query = Appointments.query.filter_by(user_id=current_user.id).all()
        active_admission = Admission.query.filter_by(patient_id=current_user.id, status='Admitted').first()
    
    query.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]
    
    return render_template('bookings/appointment_history.html', query=query, page_title="Appointment Log", prescribed_apt_ids=prescribed_apt_ids, active_admission=active_admission)

@patient_bp.route('/upcoming_bookings')
@login_required
def upcoming_bookings():
    today = date.today()
    now = datetime.now().time()
    active_admission = None

    if current_user.usertype == "Doctor":
        raw_query = Appointments.query.filter(
            Appointments.doctor == current_user.username, 
            Appointments.date >= str(today)
        ).all()
    else:
        raw_query = Appointments.query.filter(
            Appointments.user_id == current_user.id, 
            Appointments.date >= str(today)
        ).all()
        active_admission = Admission.query.filter_by(patient_id=current_user.id, status='Admitted').first()
    
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]

    upcoming_list = []
    for apt in raw_query:
        apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
        if str(apt.date) == str(today) and apt_time <= now:
            continue
        if apt.slot in ['Completed', 'Missed', 'Attended', 'Cancelled'] or apt.apt_id in prescribed_apt_ids:
            continue
        upcoming_list.append(apt)
        
    upcoming_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'))

    return render_template('bookings/appointment_history.html', query=upcoming_list, page_title="Upcoming Appointments", prescribed_apt_ids=[], active_admission=active_admission)

@patient_bp.route('/past_records')
@login_required
def past_records():
    today_str = str(date.today()) 
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]
    active_admission = None

    if current_user.usertype == "Doctor":
        raw_query = Appointments.query.filter_by(doctor=current_user.username).all()
    else:
        raw_query = Appointments.query.filter_by(user_id=current_user.id).all()
        active_admission = Admission.query.filter_by(patient_id=current_user.id, status='Admitted').first()
    
    history_list = []
    for apt in raw_query:
        is_completed = (apt.apt_id in prescribed_apt_ids) or (apt.slot == 'Completed')
        is_pending_rx = (apt.slot == 'Attended')
        is_past_unverified = (str(apt.date) < today_str and apt.slot not in ['Completed', 'Attended', 'Missed', 'Cancelled'])
        
        if is_completed or is_pending_rx or is_past_unverified:
            history_list.append(apt)

    history_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)
    return render_template('bookings/appointment_history.html', query=history_list, page_title="Patient History", is_past_record=True, prescribed_apt_ids=prescribed_apt_ids, active_admission=active_admission)


# ── BILLING & PAYMENT GATEWAY ────────────────────────────────────────

@patient_bp.route('/my_bills')
@login_required
def my_bills():
    if current_user.usertype != 'Patient':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('main.index'))
    
    my_invoices = Billing.query.filter_by(user_id=current_user.id).order_by(Billing.issued_on.desc()).all()
    return render_template('bookings/my_bills.html', invoices=my_invoices)

@patient_bp.route('/bills/<int:bill_id>/invoice')
@login_required
def view_invoice(bill_id):
    invoice = Billing.query.get_or_404(bill_id)
    if not can_access_invoice(current_user, invoice):
        flash("Security Alert: Unauthorized access to invoice.", "danger")
        return redirect(url_for('patient.my_bills'))
        
    if invoice.status == 'Paid':
        return redirect(url_for('patient.view_receipt', bill_id=bill_id))
        
    return render_template('bookings/pay_invoice.html', invoice=invoice)

@patient_bp.route('/bills/<int:bill_id>/pay', methods=['POST'])
@login_required
def process_payment(bill_id):
    if current_user.usertype != 'Patient':
        return redirect(url_for('main.index'))

    invoice = Billing.query.get_or_404(bill_id)
    if not can_access_invoice(current_user, invoice):
        flash("Security Alert: Unauthorized access.", "danger")
        return redirect(url_for('patient.my_bills'))

    payment_mode = request.form.get('payment_mode')
    bank_name = request.form.get('bank_name', None)

    if not payment_mode:
        flash("Error: Please select a valid payment method.", "warning")
        return redirect(url_for('patient.view_invoice', bill_id=bill_id))

    # Process via BillingService: sets demo_simulation flag with clear disclosure
    success, message, updated_inv = BillingService.process_demo_payment(
        bill_id=bill_id,
        payment_mode=payment_mode,
        patient_user=current_user,
        bank_name=bank_name
    )

    if success:
        flash(message, "info")
        return redirect(url_for('patient.view_receipt', bill_id=bill_id))
    else:
        flash(message, "danger")
        return redirect(url_for('patient.view_invoice', bill_id=bill_id))

@patient_bp.route('/bills/<int:bill_id>/receipt')
@login_required
def view_receipt(bill_id):
    invoice = Billing.query.get_or_404(bill_id)
    if not can_access_invoice(current_user, invoice):
        flash("Unauthorized access to receipt.", "danger")
        return redirect(url_for('patient.my_bills'))
        
    if invoice.status != 'Paid':
        flash('This invoice has not been settled yet.', 'warning')
        return redirect(url_for('patient.view_invoice', bill_id=bill_id))
        
    return render_template('bookings/receipt.html', invoice=invoice)
