# routes/main.py
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models import Appointments, MedicalRecord, Doctors

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.usertype == 'Admin':
            return redirect(url_for('admin.admin_dashboard'))
        
        if current_user.usertype == 'Doctor':
            today = date.today()
            now = datetime.now().time()

            todays_appointments = Appointments.query.filter_by(
                doctor=current_user.username, 
                date=today
            ).all()

            todays_appointments.sort(key=lambda x: datetime.strptime(x.time, '%I:%M %p').time())

            total_today = len(todays_appointments)
            unverified_active = []
            next_patient = None
            completed_count = 0
            waiting_count = 0
            pending_rx_count = 0 
            
            prescribed_apt_ids = [r.apt_id for r in MedicalRecord.query.all()]

            for apt in todays_appointments:
                apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
                apt.is_active = (apt_time <= now)

                if apt.apt_id in prescribed_apt_ids or apt.slot == 'Completed':
                    apt.category = 'completed'
                    completed_count += 1
                elif apt.slot == 'Missed':
                    apt.category = 'missed'
                elif apt.slot == 'Cancelled':
                    apt.category = 'cancelled'
                elif apt.slot == 'Attended':
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
                unverified_active.sort(key=lambda x: datetime.strptime(x.time, '%I:%M %p').time(), reverse=True)
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
            now = datetime.now().time()
                
            raw_upcoming = Appointments.query.filter(
                Appointments.user_id == current_user.id,
                Appointments.date >= today
            ).all()
            
            upcoming_list = []
            for apt in raw_upcoming:
                apt_time = datetime.strptime(apt.time, '%I:%M %p').time()
                if apt.date == str(today) and apt_time <= now:
                    continue
                if apt.slot == 'Scheduled': 
                    upcoming_list.append(apt)
                    
            upcoming_list.sort(key=lambda x: datetime.strptime(f"{x.date} {x.time}", '%Y-%m-%d %I:%M %p'))
            upcoming_appointments = upcoming_list[:5]
            
            return render_template('index.html', 
                                upcoming_appointments=upcoming_appointments, 
                                today_date=today.strftime('%A, %b %d, %Y'))

    return render_template('index.html')

@main_bp.route('/doctors', methods=['GET'])

def doctors():
    # 🎓 UPGRADE: Use the SQLAlchemy relationship to map the name from the User table
    raw_doctors = Doctors.query.all()
    doctors_list = [
        {'doctorname': d.user_account.username, 'dept': d.dept} 
        for d in raw_doctors
    ]
    return render_template('doctor_directory.html', all_doctors=doctors_list)
