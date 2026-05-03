# routes/doctor.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Appointments, MedicalRecord

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/cancel_apt/<int:apt_id>', methods=['POST'])
@login_required
def cancel_apt(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    if current_user.usertype == "Patient" and appointment.user_id != current_user.id:
        flash("Unauthorized! You can only cancel your own appointments.", "danger")
        return redirect(request.referrer or url_for('patient.upcoming_bookings'))
    elif current_user.usertype == "Doctor" and appointment.doctor.lower() != current_user.username.lower():
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
        flash("Unauthorized!", "danger")
        return redirect(url_for('patient.dashboard'))
    appointment = Appointments.query.get_or_404(apt_id)
    appointment.slot = 'Missed'
    db.session.commit()
    flash(f"Appointment marked as Missed.", "info")
    return redirect(request.referrer or url_for('patient.dashboard'))

@doctor_bp.route('/mark_attended/<int:apt_id>', methods=['POST'])
@login_required
def mark_attended(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized!", "danger")
        return redirect(url_for('patient.dashboard'))
    appointment = Appointments.query.get_or_404(apt_id)
    appointment.slot = 'Attended'
    db.session.commit()
    flash(f"Patient marked as Attended. Prescription is now pending.", "success")
    return redirect(request.referrer or url_for('main.index'))

@doctor_bp.route('/add_record/<int:apt_id>', methods=['GET', 'POST'])
@login_required
def add_record(apt_id):
    if current_user.usertype != "Doctor":
        flash("Unauthorized! Only doctors can add medical records.", "danger")
        return redirect(url_for('patient.dashboard'))

    appointment = Appointments.query.get_or_404(apt_id)
    existing_record = MedicalRecord.query.filter_by(apt_id=apt_id).first()
    
    if existing_record:
        flash("A medical record already exists for this appointment.", "warning")
        return redirect(url_for('doctor.view_record', apt_id=apt_id))

    if request.method == "POST":
        diagnosis = request.form.get('diagnosis', '').strip()
        prescription = request.form.get('prescription', '').strip()
        notes = request.form.get('notes', '').strip()
        
        new_record = MedicalRecord(apt_id=apt_id, diagnosis=diagnosis, prescription=prescription, notes=notes)
        db.session.add(new_record)
        appointment.slot = 'Completed'
        db.session.commit()
        
        flash("Medical record saved successfully!", "success")
        return redirect(url_for('main.index'))
        
    return render_template('records/add_record.html', appointment=appointment)

@doctor_bp.route('/view_record/<int:apt_id>')
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

    if appointment.doctor.lower() != current_user.username.lower():
         flash("Unauthorized access. You cannot edit another doctor's patient record.", "danger")
         return redirect(url_for('patient.dashboard'))

    if request.method == "POST":
        record.diagnosis = request.form.get('diagnosis', '').strip()
        record.prescription = request.form.get('prescription', '').strip()
        record.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash("Medical record updated successfully!", "success")
        return redirect(url_for('patient.past_records'))
        
    return render_template('records/edit_record.html', appointment=appointment, record=record)