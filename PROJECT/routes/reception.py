# routes/reception.py
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from models import db, User, Appointments, Doctors, Billing, AuditLog
from authorization import require_roles
from services.scheduling import SchedulingService

reception_bp = Blueprint('reception', __name__, url_prefix='/reception')

@reception_bp.route('/queue')
@login_required
@require_roles('Receptionist', 'Admin', 'Doctor')
def queue_board():
    """Receptionist OPD Command Board: real-time patient queue and check-in tracking."""
    today = date.today().isoformat()
    selected_date = request.args.get('date', today)
    selected_doctor = request.args.get('doctor', '')

    query = Appointments.query.filter_by(date=selected_date)
    if selected_doctor:
        query = query.filter_by(doctor=selected_doctor)

    all_appointments = query.order_by(Appointments.time.asc()).all()

    # Calculate queue statistics
    waiting_count = sum(1 for a in all_appointments if a.slot in ('Scheduled', 'CheckedIn'))
    with_doc_count = sum(1 for a in all_appointments if a.slot == 'Attended')
    completed_count = sum(1 for a in all_appointments if a.slot == 'Completed')
    missed_count = sum(1 for a in all_appointments if a.slot in ('Missed', 'Cancelled'))

    all_doctors = Doctors.query.all()
    doctor_names = [d.user_account.username for d in all_doctors if d.user_account]

    return render_template(
        'reception/queue_board.html',
        appointments=all_appointments,
        selected_date=selected_date,
        selected_doctor=selected_doctor,
        doctor_names=doctor_names,
        waiting_count=waiting_count,
        with_doc_count=with_doc_count,
        completed_count=completed_count,
        missed_count=missed_count
    )

@reception_bp.route('/check_in/<int:apt_id>', methods=['POST'])
@login_required
@require_roles('Receptionist', 'Admin')
def check_in(apt_id):
    """Mark a patient as checked-in at reception desk and issue queue token."""
    appointment = Appointments.query.get_or_404(apt_id)
    if appointment.slot not in ('Scheduled', 'Draft'):
        flash(f"Appointment is already in '{appointment.slot}' status.", "info")
        return redirect(url_for('reception.queue_board'))

    appointment.slot = 'CheckedIn'
    
    # Ensure token number exists
    if not appointment.token_number:
        daily_count = Appointments.query.filter_by(doctor=appointment.doctor, date=appointment.date).count()
        appointment.token_number = daily_count

    audit = AuditLog(
        apt_id=appointment.apt_id,
        user_id=appointment.user_id,
        action=f"PATIENT CHECKED IN (Token #{appointment.token_number}) by {current_user.username}",
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Patient {appointment.patient.username} successfully Checked In. Queue Token #{appointment.token_number} issued.", "success")
    return redirect(url_for('reception.queue_board'))

@reception_bp.route('/register_patient', methods=['GET', 'POST'])
@login_required
@require_roles('Receptionist', 'Admin')
def register_patient():
    """Register a new patient at front desk with duplicate detection and MRN creation."""
    potential_duplicate = None
    if request.method == 'POST':
        full_name = request.form.get('username', '').strip()
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender', '').strip()
        email = request.form.get('email', '').strip()
        allergies = request.form.get('allergies', 'None known').strip()
        blood_group = request.form.get('blood_group', '').strip()
        force_create = request.form.get('force_create', 'false') == 'true'

        if not all([full_name, phone]):
            flash("Patient name and phone number are required.", "danger")
            return render_template('reception/register_patient.html')

        # Duplicate detection check
        existing = User.query.filter(
            (User.phone == phone) | ((User.username.ilike(full_name)) & (User.usertype == 'Patient'))
        ).first()

        if existing and not force_create:
            potential_duplicate = existing
            flash(f"Potential Duplicate Detected: Existing patient found with MRN {existing.mrn} and Phone {existing.phone}.", "warning")
            return render_template('reception/register_patient.html', duplicate=potential_duplicate, form_data=request.form)

        # Generate unique MRN
        current_year = datetime.now().year
        count = User.query.filter_by(usertype='Patient').count() + 1
        mrn = f"MRN-{current_year}-{count:04d}"

        # Default synthetic/placeholder email if none provided
        patient_email = email if email else f"patient_{phone.replace('-', '')}@hospital.local"
        
        # Verify email uniqueness
        if User.query.filter_by(email=patient_email).first():
            patient_email = f"patient_{count}_{phone.replace('-', '')}@hospital.local"

        new_patient = User(
            username=full_name,
            usertype='Patient',
            email=patient_email,
            password=generate_password_hash('PatientPass@2026'),
            phone=phone,
            gender=gender,
            mrn=mrn,
            allergies=allergies,
            blood_group=blood_group
        )
        db.session.add(new_patient)
        db.session.commit()

        flash(f"Patient registered successfully! MRN Assigned: {mrn}", "success")
        return redirect(url_for('reception.queue_board'))

    return render_template('reception/register_patient.html')
