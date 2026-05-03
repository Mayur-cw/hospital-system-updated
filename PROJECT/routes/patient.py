# routes/patient.py
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Appointments, Doctors, MedicalRecord

patient_bp = Blueprint('patient', __name__)

def is_slot_booked(requested_date, requested_time, target_doctor, current_apt_id=None):
    query = Appointments.query.filter_by(date=requested_date, time=requested_time, doctor=target_doctor)
    if current_apt_id:
        query = query.filter(Appointments.apt_id != current_apt_id)
    bookings = query.all()
    active_bookings = [b for b in bookings if b.slot not in ['Cancelled', 'Missed']]
    return len(active_bookings) > 0

@patient_bp.route('/get_booked_slots', methods=['POST'])
@login_required
def get_booked_slots():
    data = request.get_json()
    req_date = data.get('date')
    req_doctor = data.get('doctor')
    current_apt_id = data.get('current_pid') 

    if not req_date or not req_doctor:
        return jsonify({'booked_times': []})

    query = Appointments.query.filter_by(date=req_date, doctor=req_doctor)
    if current_apt_id:
        query = query.filter(Appointments.apt_id != current_apt_id)

    bookings = query.all()
    booked_times = [b.time for b in bookings if b.slot not in ['Cancelled', 'Missed']]
    return jsonify({'booked_times': booked_times})

@patient_bp.route('/patients', methods=['POST', 'GET'])
@login_required
def patient_booking():
    doct = Doctors.query.all()

    if request.method == "POST":
        slot    = request.form.get('slot', '').strip()
        disease = request.form.get('disease', '').strip()
        time    = request.form.get('time', '').strip()
        date_str= request.form.get('date', '').strip()
        dept    = request.form.get('dept', '').strip()
        doctor  = request.form.get('doctor', '').strip()

        if not all([slot, disease, time, date_str, dept, doctor]):
            flash("All fields are required.", "danger")
            return render_template('bookings/book_appointment.html', doct=doct)

        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today_date = datetime.today().date()
            
            if appointment_date < today_date:
                flash("Error: You cannot book an appointment in the past.", "danger")
                return redirect(url_for('patient.patient_booking'))
                
            if appointment_date == today_date:
                appointment_time = datetime.strptime(time, '%I:%M %p').time()
                current_time = datetime.now().time()
                
                if appointment_time < current_time:
                    flash("Error: That time slot has already passed today. Please select a future time.", "danger")
                    return redirect(url_for('patient.patient_booking'))
                    
        except ValueError:
            flash("Invalid date or time format.", "danger")
            return redirect(url_for('patient.patient_booking'))

        if is_slot_booked(date_str, time, doctor):
            flash(f"Slot Unavailable: Dr. {doctor.capitalize()} is already booked at {time}. Please choose another slot.", "warning")
            return redirect(url_for('patient.patient_booking'))

        new_appointment = Appointments(
            user_id=current_user.id, 
            slot=slot, disease=disease, time=time,
            date=date_str, dept=dept, doctor=doctor
        )
        db.session.add(new_appointment)
        db.session.commit()
        
        return redirect(url_for('patient.booking_success', apt_id=new_appointment.apt_id))

    pre_dept = request.args.get('dept', '')
    pre_doc = request.args.get('doctor', '')

    return render_template('bookings/book_appointment.html', doct=doct, pre_dept=pre_dept, pre_doc=pre_doc)

@patient_bp.route('/booking_success/<int:apt_id>')
@login_required
def booking_success(apt_id):
    appointment = Appointments.query.get_or_404(apt_id)
    if current_user.usertype != "Doctor" and appointment.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('main.index'))
    return render_template('bookings/booking_success.html', appointment=appointment)

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.usertype == "Doctor":
        query = Appointments.query.filter_by(doctor=current_user.username).all()
    else:
        query = Appointments.query.filter_by(user_id=current_user.id).all()
    
    query.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]
    
    return render_template('bookings/appointment_history.html', query=query, page_title="Appointment Log", prescribed_apt_ids=prescribed_apt_ids)

@patient_bp.route('/upcoming_bookings')
@login_required
def upcoming_bookings():
    today = date.today()
    now = datetime.now().time()

    if current_user.usertype == "Doctor":
        raw_query = Appointments.query.filter(
            Appointments.doctor == current_user.username, 
            Appointments.date >= today
        ).all()
    else:
        raw_query = Appointments.query.filter(
            Appointments.user_id == current_user.id, 
            Appointments.date >= today
        ).all()
    
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]

    upcoming_list = []
    for apt in raw_query:
        apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
        if apt.date == today and apt_time <= now:
            continue
        if apt.slot in ['Completed', 'Missed', 'Attended', 'Cancelled'] or apt.apt_id in prescribed_apt_ids:
            continue
        upcoming_list.append(apt)
        
    upcoming_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'))

    return render_template('bookings/appointment_history.html', query=upcoming_list, page_title="Upcoming Appointments", prescribed_apt_ids=[])

@patient_bp.route('/past_records')
@login_required
def past_records():
    today_str = str(date.today()) 
    records = MedicalRecord.query.all()
    prescribed_apt_ids = [r.apt_id for r in records]

    if current_user.usertype == "Doctor":
        raw_query = Appointments.query.filter_by(doctor=current_user.username).all()
    else:
        raw_query = Appointments.query.filter_by(user_id=current_user.id).all()
    
    history_list = []
    for apt in raw_query:
        is_completed = (apt.apt_id in prescribed_apt_ids) or (apt.slot == 'Completed')
        is_pending_rx = (apt.slot == 'Attended')
        is_past_unverified = (str(apt.date) < today_str and apt.slot not in ['Completed', 'Attended', 'Missed', 'Cancelled'])
        
        if is_completed or is_pending_rx or is_past_unverified:
            history_list.append(apt)

    history_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'), reverse=True)
    return render_template('bookings/appointment_history.html', query=history_list, page_title="Patient History", is_past_record=True, prescribed_apt_ids=prescribed_apt_ids)