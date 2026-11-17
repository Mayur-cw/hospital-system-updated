# routes/main.py
from datetime import date, datetime

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user

from hms.extensions import db
from hms.models.appointment import Appointment, AppointmentStatus
from hms.models.department import Department
from hms.models.doctor import Doctor
from hms.models.record import MedicalRecord
from hms.models.user import User

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.usertype == 'Admin':
            return redirect(url_for('admin.admin_dashboard'))

        if current_user.usertype == 'Doctor':
            today = date.today()
            now = datetime.now()

            doc_profile = Doctor.query.filter_by(user_id=current_user.id).first()
            doc_id = doc_profile.id if doc_profile else None

            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())

            if doc_id:
                todays_appointments = Appointment.query.filter(
                    Appointment.doctor_id == doc_id,
                    Appointment.starts_at >= today_start,
                    Appointment.starts_at <= today_end
                ).order_by(Appointment.starts_at.asc()).all()
            else:
                todays_appointments = []

            total_today = len(todays_appointments)
            unverified_active = []
            next_patient = None
            completed_count = 0
            waiting_count = 0
            pending_rx_count = 0

            # B-20: Fetch only prescribed appointment IDs for today's appointments
            if todays_appointments:
                apt_ids = [a.id for a in todays_appointments]
                prescribed_query = db.session.query(MedicalRecord.appointment_id).filter(
                    MedicalRecord.appointment_id.in_(apt_ids)
                ).all()
                prescribed_apt_ids = {r[0] for r in prescribed_query}
            else:
                prescribed_apt_ids = set()

            for apt in todays_appointments:
                apt.is_active = (apt.starts_at <= now)

                if apt.id in prescribed_apt_ids or apt.status == AppointmentStatus.COMPLETED:
                    apt.category = 'completed'
                    completed_count += 1
                elif apt.status == AppointmentStatus.MISSED:
                    apt.category = 'missed'
                elif apt.status == AppointmentStatus.CANCELLED:
                    apt.category = 'cancelled'
                elif apt.status in ('Attended', AppointmentStatus.CHECKED_IN):
                    apt.category = 'pending_rx'
                    pending_rx_count += 1
                else:
                    apt.category = 'waiting'
                    waiting_count += 1
                    if apt.is_active:
                        unverified_active.append(apt)
                    else:
                        if not next_patient:
                            next_patient = apt

            if unverified_active:
                unverified_active.sort(key=lambda x: x.starts_at, reverse=True)
                current_patient = unverified_active[0]
            else:
                current_patient = None

            formatted_date = today.strftime('%A, %b %d, %Y')

            return render_template('index.html',
                                   all_queue=todays_appointments,
                                   total_today=total_today,
                                   current_patient=current_patient,
                                   next_patient=next_patient,
                                   waiting_count=waiting_count,
                                   completed_count=completed_count,
                                   pending_rx_count=pending_rx_count,
                                   today_date=formatted_date)

        elif current_user.usertype == 'Patient':
            today = date.today()
            now = datetime.now()

            # B-08 & B-09: Direct typed relational filtering on starts_at
            upcoming_appointments = Appointment.query.filter(
                Appointment.patient_id == current_user.id,
                Appointment.starts_at >= now,
                Appointment.status == AppointmentStatus.SCHEDULED
            ).order_by(Appointment.starts_at.asc()).limit(5).all()

            return render_template('index.html',
                                   upcoming_appointments=upcoming_appointments,
                                   today_date=today.strftime('%A, %b %d, %Y'))

    return render_template('index.html')


@main_bp.route('/search', methods=['GET', 'POST'])
def search():
    """B-02 & F-02: Global search across doctors, departments, patients, and wards."""
    query = (request.args.get('search') or request.form.get('search') or request.args.get('q') or '').strip()

    if not query:
        return render_template('search_results.html', query='', results_count=0, doctors=[], patients=[], rooms=[])

    term = f"%{query}%"

    # Search Doctors
    doc_query = db.session.query(Doctor, User).join(User, Doctor.user_id == User.id).outerjoin(Department, Doctor.department_id == Department.id)
    doc_matches = doc_query.filter(
        db.or_(
            User.username.ilike(term),
            Department.name.ilike(term),
            Doctor.qualifications.ilike(term),
            Doctor.bio.ilike(term)
        )
    ).all()

    doctor_results = []
    for doc, u in doc_matches:
        dept_name = doc.department.name if doc.department else (doc.dept or "General Medicine")
        doctor_results.append({
            'id': doc.id,
            'name': u.username,
            'email': u.email,
            'dept': dept_name,
            'qualifications': doc.qualifications,
            'fee': doc.consultation_fee
        })

    # Search Patients (restricted to Admin and Doctor)
    patient_results = []
    if current_user.is_authenticated and current_user.usertype in ('Admin', 'Doctor'):
        p_matches = User.query.filter(
            User.usertype == 'Patient',
            db.or_(
                User.username.ilike(term),
                User.email.ilike(term),
                User.phone.ilike(term)
            )
        ).limit(20).all()
        patient_results = p_matches

    # Search Rooms (Admin only)
    room_results = []
    if current_user.is_authenticated and current_user.usertype == 'Admin':
        from hms.models.admission import Room
        room_results = Room.query.filter(
            db.or_(
                Room.room_number.ilike(term),
                Room.ward_type.ilike(term)
            )
        ).limit(20).all()

    results_count = len(doctor_results) + len(patient_results) + len(room_results)

    return render_template(
        'search_results.html',
        query=query,
        results_count=results_count,
        doctors=doctor_results,
        patients=patient_results,
        rooms=room_results
    )


@main_bp.route('/doctors', methods=['GET'])
def doctors():
    raw_doctors = Doctor.query.all()
    doctors_list = []
    for d in raw_doctors:
        u_name = d.user.username if d.user else "Physician"
        dept_name = d.department.name if d.department else (d.dept or "General Medicine")
        doctors_list.append({
            'doctorname': u_name,
            'dept': dept_name,
            'fee': d.consultation_fee,
            'qualifications': d.qualifications
        })
    return render_template('doctor_directory.html', all_doctors=doctors_list)
