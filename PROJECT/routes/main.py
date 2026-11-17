# routes/main.py
from datetime import date, datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import db, User, Appointments, MedicalRecord, Doctors, Admission, Billing

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
            
            # 🏥 Inpatient Admission & Room Tracking (Admitted OR Billing Pending)
            active_admission = Admission.query.filter(
                Admission.patient_id == current_user.id,
                Admission.status.in_(['Admitted', 'Billing Pending'])
            ).order_by(Admission.admission_date.desc()).first()

            admission_bill = None
            stay_days = 1
            est_total = Decimal('0.00')
            if active_admission:
                adm_date = active_admission.admission_date or datetime.now()
                delta = datetime.now() - adm_date
                stay_days = max(1, delta.days)
                rate = Decimal(str(active_admission.room.rate_per_day))
                calc_days = active_admission.actual_days if active_admission.actual_days else stay_days
                est_total = Decimal(calc_days) * rate
                admission_bill = Billing.query.filter_by(apt_id=active_admission.apt_id).first()
                if admission_bill and admission_bill.amount:
                    est_total = admission_bill.amount
                
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
            
            # 💳 Pending / Unpaid Invoices
            unpaid_bills = Billing.query.filter_by(
                user_id=current_user.id,
                status='Unpaid'
            ).order_by(Billing.issued_on.desc()).all()
            total_unpaid = sum((b.amount for b in unpaid_bills if b.amount), Decimal('0.00'))

            return render_template('index.html', 
                                upcoming_appointments=upcoming_appointments, 
                                today_date=today.strftime('%A, %b %d, %Y'),
                                active_admission=active_admission,
                                stay_days=stay_days,
                                est_total=est_total,
                                admission_bill=admission_bill,
                                unpaid_bills=unpaid_bills,
                                total_unpaid=total_unpaid)

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


@main_bp.route('/search', methods=['GET', 'POST'])
def global_search():
    query = (request.args.get('q') or request.args.get('search') or request.form.get('search') or '').strip()
    
    # If patient attempts to search, redirect to dashboard
    if current_user.is_authenticated and current_user.usertype == 'Patient':
        return redirect(url_for('patient.dashboard'))

    results = {
        'doctors': [],
        'patients': [],
        'staff': []
    }
    
    if not query:
        return render_template('search_results.html', query='', results=results, total_count=0)

    search_term = f"%{query}%"

    if not current_user.is_authenticated or current_user.usertype == 'Guest':
        # Public search: search doctors by name or department
        docs = Doctors.query.join(User, Doctors.user_id == User.id).filter(
            (User.username.ilike(search_term)) | 
            (Doctors.dept.ilike(search_term)) |
            (User.email.ilike(search_term))
        ).all()
        for d in docs:
            results['doctors'].append({
                'id': d.user_account.id,
                'name': d.user_account.username,
                'email': d.user_account.email,
                'dept': d.dept
            })

    elif current_user.usertype == 'Doctor':
        # Doctor search: search patient profiles
        patients = User.query.filter_by(usertype='Patient').filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) | 
            (User.phone.ilike(search_term)) |
            (User.mrn.ilike(search_term))
        ).all()
        
        for p in patients:
            # Check appointments with this doctor
            my_apts = Appointments.query.filter_by(user_id=p.id, doctor=current_user.username).order_by(Appointments.date.desc()).all()
            # Check if admitted
            admission = Admission.query.filter_by(patient_id=p.id, status='Admitted').first()
            results['patients'].append({
                'id': p.id,
                'name': p.username,
                'email': p.email,
                'phone': p.phone or 'Not Provided',
                'gender': p.gender or 'Unspecified',
                'mrn': p.mrn or f'PID-{p.id}',
                'my_appointments': my_apts,
                'active_admission': admission
            })

    elif current_user.usertype == 'Admin':
        # Admin search: search doctors, patients, staff
        # 1. Doctors
        docs = Doctors.query.join(User, Doctors.user_id == User.id).filter(
            (User.username.ilike(search_term)) | 
            (Doctors.dept.ilike(search_term)) |
            (User.email.ilike(search_term))
        ).all()
        for d in docs:
            apt_count = Appointments.query.filter_by(doctor=d.user_account.username).count()
            results['doctors'].append({
                'id': d.user_account.id,
                'name': d.user_account.username,
                'email': d.user_account.email,
                'dept': d.dept,
                'appointment_count': apt_count
            })

        # 2. Patients
        patients = User.query.filter_by(usertype='Patient').filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) | 
            (User.phone.ilike(search_term)) |
            (User.mrn.ilike(search_term))
        ).all()
        for p in patients:
            apt_count = Appointments.query.filter_by(user_id=p.id).count()
            results['patients'].append({
                'id': p.id,
                'name': p.username,
                'email': p.email,
                'phone': p.phone or 'Not Provided',
                'gender': p.gender or 'Unspecified',
                'mrn': p.mrn or f'PID-{p.id}',
                'appointment_count': apt_count
            })

        # 3. Staff
        staff_users = User.query.filter(User.usertype.in_(['Admin', 'Cashier', 'Receptionist'])).filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) | 
            (User.usertype.ilike(search_term))
        ).all()
        for s in staff_users:
            results['staff'].append({
                'id': s.id,
                'name': s.username,
                'email': s.email,
                'role': s.usertype,
                'phone': s.phone or 'Not Provided'
            })

    elif current_user.usertype == 'Cashier':
        # Cashier: search patients and bills
        patients = User.query.filter_by(usertype='Patient').filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) | 
            (User.phone.ilike(search_term))
        ).all()
        for p in patients:
            results['patients'].append({
                'id': p.id,
                'name': p.username,
                'email': p.email,
                'phone': p.phone or 'Not Provided',
                'gender': p.gender or 'Unspecified',
                'mrn': p.mrn or f'PID-{p.id}'
            })

    total_count = len(results['doctors']) + len(results['patients']) + len(results['staff'])
    return render_template('search_results.html', query=query, results=results, total_count=total_count)


@main_bp.route('/api/search', methods=['GET'])
def api_search():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'results': [], 'total': 0})
        
    search_term = f"%{query}%"
    items = []

    if not current_user.is_authenticated or current_user.usertype == 'Guest':
        docs = Doctors.query.join(User, Doctors.user_id == User.id).filter(
            (User.username.ilike(search_term)) | (Doctors.dept.ilike(search_term))
        ).limit(6).all()
        for d in docs:
            items.append({
                'type': 'doctor',
                'title': d.user_account.username,
                'subtitle': d.dept,
                'badge': 'Doctor',
                'badge_color': 'primary',
                'icon': 'fa-user-md',
                'url': url_for('main.global_search', q=d.user_account.username)
            })

    elif current_user.usertype == 'Doctor':
        # Search patients
        patients = User.query.filter_by(usertype='Patient').filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) | 
            (User.phone.ilike(search_term)) |
            (User.mrn.ilike(search_term))
        ).limit(8).all()
        for p in patients:
            items.append({
                'type': 'patient',
                'title': p.username,
                'subtitle': f"MRN: {p.mrn or 'PID-'+str(p.id)} • {p.email}",
                'badge': 'Patient',
                'badge_color': 'info',
                'icon': 'fa-user-injured',
                'url': url_for('main.global_search', q=p.username)
            })

    elif current_user.usertype == 'Admin':
        # Search doctors
        docs = Doctors.query.join(User, Doctors.user_id == User.id).filter(
            (User.username.ilike(search_term)) | (Doctors.dept.ilike(search_term))
        ).limit(4).all()
        for d in docs:
            items.append({
                'type': 'doctor',
                'title': d.user_account.username,
                'subtitle': f"Specialty: {d.dept}",
                'badge': 'Doctor',
                'badge_color': 'primary',
                'icon': 'fa-user-md',
                'url': url_for('admin.admin_doctors')
            })

        # Search patients
        patients = User.query.filter_by(usertype='Patient').filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) | 
            (User.mrn.ilike(search_term))
        ).limit(4).all()
        for p in patients:
            items.append({
                'type': 'patient',
                'title': p.username,
                'subtitle': f"Patient ID: PID-{p.id} • {p.email}",
                'badge': 'Patient',
                'badge_color': 'success',
                'icon': 'fa-procedures',
                'url': url_for('admin.admin_patients', search=p.username)
            })

        # Search staff
        staff = User.query.filter(User.usertype.in_(['Admin', 'Cashier', 'Receptionist'])).filter(
            (User.username.ilike(search_term)) | (User.usertype.ilike(search_term))
        ).limit(3).all()
        for s in staff:
            items.append({
                'type': 'staff',
                'title': s.username,
                'subtitle': f"System Role: {s.usertype}",
                'badge': s.usertype,
                'badge_color': 'warning',
                'icon': 'fa-user-shield',
                'url': url_for('admin.admin_staff')
            })

    return jsonify({'results': items, 'total': len(items)})
