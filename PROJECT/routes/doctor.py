# routes/doctor.py
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db, Appointments, MedicalRecord, Billing, Room, Admission, Doctors
from authorization import can_modify_appointment_status, can_chart_encounter, can_discharge_admission
from services.clinical import ClinicalService
from services.inpatient import InpatientService

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/appointments')
@doctor_bp.route('/doctor/appointments')
@login_required
def appointments_workspace():
    return redirect(url_for('patient.dashboard'))

@doctor_bp.route('/cancel_apt/<int:apt_id>', methods=['POST'])
@login_required
def cancel_apt(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    if current_user.usertype == "Patient" and appointment.user_id != current_user.id:
        flash("Unauthorized! You can only cancel your own appointments.", "danger")
        return redirect(request.referrer or url_for('patient.upcoming_bookings'))
    elif current_user.usertype == "Doctor" and not can_modify_appointment_status(current_user, appointment):
        flash("Unauthorized! You can only cancel your own schedule.", "danger")
        return redirect(request.referrer or url_for('patient.dashboard'))

    appointment.slot = 'Cancelled'
    db.session.commit()
    flash("Appointment has been successfully cancelled.", "warning")
    return redirect(request.referrer or url_for('patient.dashboard'))

@doctor_bp.route('/mark_missed/<int:apt_id>', methods=['POST'])
@login_required
def mark_missed(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized! Doctor access required.", "danger")
        return redirect(url_for('patient.dashboard'))
        
    appointment = Appointments.query.get_or_404(apt_id)
    if not can_modify_appointment_status(current_user, appointment):
        flash("Access Denied: You cannot modify appointments assigned to another physician.", "danger")
        return redirect(url_for('patient.dashboard'))

    appointment.slot = 'Missed'
    db.session.commit()
    flash("Appointment marked as Missed.", "info")
    return redirect(request.referrer or url_for('patient.dashboard'))

@doctor_bp.route('/mark_attended/<int:apt_id>', methods=['POST'])
@login_required
def mark_attended(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized! Doctor access required.", "danger")
        return redirect(url_for('patient.dashboard'))
        
    appointment = Appointments.query.get_or_404(apt_id)
    if not can_modify_appointment_status(current_user, appointment):
        flash("Access Denied: You cannot modify appointments assigned to another physician.", "danger")
        return redirect(url_for('patient.dashboard'))

    appointment.slot = 'Attended'
    db.session.commit()
    flash("Patient marked as Attended. Clinical charting workspace is now open.", "success")
    return redirect(url_for('doctor.add_record', apt_id=apt_id))

@doctor_bp.route('/add_record/<int:apt_id>', methods=['GET', 'POST'])
@login_required
def add_record(apt_id):
    if current_user.usertype != "Doctor" and current_user.usertype != "Admin":
        flash("Unauthorized! Only clinicians can document medical records.", "danger")
        return redirect(url_for('patient.dashboard'))

    appointment = Appointments.query.get_or_404(apt_id)
    if not can_chart_encounter(current_user, appointment):
        flash("Access Denied: You can only document medical records for your assigned patients.", "danger")
        return redirect(url_for('patient.dashboard'))

    existing_record = MedicalRecord.query.filter_by(apt_id=apt_id).first()
    if existing_record:
        flash("A signed medical record already exists for this appointment.", "warning")
        return redirect(url_for('doctor.view_record', apt_id=apt_id))

    if request.method == "POST":
        diagnosis = request.form.get('diagnosis', '').strip()
        prescription = request.form.get('prescription', '').strip()
        notes = request.form.get('notes', '').strip()
        room_id = request.form.get('room_id')
        action = request.form.get('action', 'sign')

        if not diagnosis or not prescription:
            flash("Diagnosis and prescription are mandatory clinical fields.", "danger")
            available_rooms = Room.query.filter_by(status='Available').all()
            return render_template('records/add_record.html', appointment=appointment, available_rooms=available_rooms)

        success, message, record = ClinicalService.save_medical_record(
            apt_id=apt_id,
            diagnosis=diagnosis,
            prescription=prescription,
            notes=notes,
            doctor_user=current_user,
            action=action,
            room_id=room_id
        )

        if success:
            flash(message, "success")
            return redirect(url_for('main.index'))
        else:
            flash(message, "danger")
            return redirect(url_for('doctor.add_record', apt_id=apt_id))

    available_rooms = Room.query.filter_by(status='Available').all()
    return render_template('records/add_record.html', appointment=appointment, available_rooms=available_rooms)

@doctor_bp.route('/my_admissions')
@login_required
def my_admissions():
    if current_user.usertype != "Doctor":
        return redirect(url_for('main.index'))
    
    doc_profile = Doctors.query.filter_by(user_id=current_user.id).first()
    doc_did = doc_profile.did if doc_profile else 0
    my_patients = Admission.query.filter_by(doctor_id=doc_did, status='Admitted').all()
    
    return render_template('records/doctor_admissions.html', admissions=my_patients)

@doctor_bp.route('/discharge_patient', methods=['POST'])
@login_required
def discharge_patient():
    if current_user.usertype != "Doctor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('main.index'))
        
    admission_id = request.form.get('admission_id')
    admission = Admission.query.get_or_404(admission_id)
    
    if not can_discharge_admission(current_user, admission):
        flash("Access Denied: You cannot discharge patients under another physician's care.", "danger")
        return redirect(url_for('main.index'))

    summary = request.form.get('discharge_summary', '').strip()
    success, message, bill = InpatientService.discharge_patient(
        admission_id=admission_id,
        actor=current_user,
        discharge_summary=summary
    )
    
    flash(message, "success" if success else "warning")
    return redirect(url_for('doctor.my_admissions'))

@doctor_bp.route('/view_record/<int:apt_id>')
@doctor_bp.route('/doctor/view_record/<int:apt_id>')
@login_required
def view_record(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    record = MedicalRecord.query.filter_by(apt_id=apt_id).first()
    
    if current_user.usertype == "Patient" and appointment.user_id != current_user.id:
        flash("Unauthorized access to medical records.", "danger")
        return redirect(url_for('patient.dashboard'))
    elif current_user.usertype == "Doctor" and appointment.doctor.lower() != current_user.username.lower():
         flash("Unauthorized access. You did not attend this patient.", "danger")
         return redirect(url_for('patient.dashboard'))

    if not record:
        flash("No medical record has been generated yet.", "info")
        return redirect(url_for('patient.past_records'))
        
    return render_template('records/view_record.html', appointment=appointment, record=record)

@doctor_bp.route('/edit_record/<int:apt_id>', methods=['GET', 'POST'])
@login_required
def edit_record(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized! Only doctors can edit medical records.", "danger")
        return redirect(url_for('patient.dashboard'))

    appointment = Appointments.query.get_or_404(apt_id)
    record = MedicalRecord.query.filter_by(apt_id=apt_id).first()

    if not record:
        flash("No medical record exists to edit yet.", "warning")
        return redirect(url_for('doctor.add_record', apt_id=apt_id))

    if not can_chart_encounter(current_user, appointment):
         flash("Unauthorized access. You cannot edit another doctor's patient record.", "danger")
         return redirect(url_for('patient.dashboard'))

    if request.method == "POST":
        new_diagnosis = request.form.get('diagnosis', '').strip()
        new_prescription = request.form.get('prescription', '').strip()
        amendment_reason = request.form.get('amendment_reason', '').strip()

        if not amendment_reason:
            flash("Clinical Integrity Requirement: An explicit amendment reason is mandatory to modify a signed chart.", "danger")
            return render_template('records/edit_record.html', appointment=appointment, record=record)

        success, message = ClinicalService.amend_medical_record(
            record_id=record.record_id,
            new_diagnosis=new_diagnosis,
            new_prescription=new_prescription,
            amendment_reason=amendment_reason,
            doctor_user=current_user
        )

        flash(message, "success" if success else "danger")
        return redirect(url_for('doctor.view_record', apt_id=apt_id))
        
    return render_template('records/edit_record.html', appointment=appointment, record=record)
