# routes/admin.py
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from hms.extensions import db
from hms.models.admission import Admission, AdmissionStatus, Room, RoomStatus
from hms.models.appointment import Appointment, AppointmentStatus
from hms.models.audit import AuditEvent
from hms.models.billing import Invoice
from hms.models.department import Department
from hms.models.doctor import Doctor
from hms.models.user import User
from hms.services.accounts import AccountsService
from hms.services.admissions import AdmissionError, AdmissionService
from hms.services.audit import AuditService

admin_bp = Blueprint('admin', __name__)

ALLOWED_WARD_TYPES = ('General', 'ICU', 'VIP', 'Maternity')


@admin_bp.before_request
@login_required
def enforce_admin_rbac():
    """Central RBAC guard for all administrator endpoints (S-05)."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.path))
    if current_user.usertype != 'Admin':
        abort(403)


# ── DASHBOARD ────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    total_patients = User.query.filter_by(usertype='Patient', is_active=True).count()
    total_doctors = Doctor.query.filter_by(is_active=True).count()

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    today_appts = Appointment.query.filter(
        Appointment.starts_at >= today_start,
        Appointment.starts_at <= today_end,
        Appointment.is_active.is_(True)
    ).count()

    total_rooms = Room.query.filter_by(is_active=True).count()
    occupied_rooms = Room.query.filter_by(status='Occupied', is_active=True).count()
    available_rooms = Room.query.filter_by(status='Available', is_active=True).count()

    all_invoices = Invoice.query.all()
    total_revenue = sum((inv.total for inv in all_invoices if inv.status == 'Paid'), Decimal('0.00'))
    pending_revenue = sum((inv.total for inv in all_invoices if inv.status != 'Paid'), Decimal('0.00'))

    recent_logs = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(8).all()

    today_schedule = Appointment.query.options(
        joinedload(Appointment.patient),
        joinedload(Appointment.doctor_rel).joinedload(Doctor.user)
    ).filter(
        Appointment.starts_at >= today_start,
        Appointment.starts_at <= today_end,
        Appointment.is_active.is_(True)
    ).order_by(Appointment.starts_at.asc()).all()

    return render_template('admin/admin_dashboard.html',
                           total_patients=total_patients,
                           total_doctors=total_doctors,
                           today_appts=today_appts,
                           total_rooms=total_rooms,
                           occupied_rooms=occupied_rooms,
                           available_rooms=available_rooms,
                           total_revenue=total_revenue,
                           pending_revenue=pending_revenue,
                           recent_logs=recent_logs,
                           today_schedule=today_schedule)


@admin_bp.route('/details')
@admin_bp.route('/audit_logs')
@login_required
def details():
    """System activity & audit trail view (D-09)."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    logs = AuditEvent.query.options(joinedload(AuditEvent.actor)).order_by(AuditEvent.created_at.desc()).all()
    return render_template('admin/audit_logs.html', posts=logs)


# ── STAFF MANAGEMENT ──────────────────────────────────────────────────

@admin_bp.route('/staff')
@login_required
def admin_staff():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    admin_users = User.query.filter_by(usertype='Admin', is_active=True).all()
    return render_template('admin/admin_staff.html', admins=admin_users)


@admin_bp.route('/add_staff', methods=['POST'])
@login_required
def add_staff():
    """B-01 & B-15: Provision new staff account with strict validation."""
    if current_user.usertype != "Admin":
        flash("Unauthorized! Only Admins can provision staff accounts.", "danger")
        return redirect(url_for('main.index'))

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    usertype = request.form.get('usertype', '').strip()
    dept = request.form.get('dept', '').strip()

    if usertype not in ('Admin', 'Doctor'):
        flash("Invalid account type specified.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    if not username or not email or not password:
        flash("All account fields are required.", "warning")
        return redirect(url_for('admin.admin_dashboard'))

    if len(password) < 8:
        flash("Temporary password must be at least 8 characters long.", "warning")
        return redirect(url_for('admin.admin_dashboard'))

    if User.query.filter_by(email=email).first():
        flash("An account with that email already exists.", "warning")
        return redirect(url_for('admin.admin_dashboard'))

    try:
        new_user = AccountsService.create_user(
            email=email,
            username=username,
            password=password,
            usertype=usertype,
            dept=dept if usertype == 'Doctor' else None,
            actor=current_user
        )
        flash(f"Success! {usertype} account for {new_user.username} has been provisioned.", "success")
    except Exception as e:
        req_id = getattr(g, 'request_id', 'ERR')
        current_app.logger.exception("Provisioning failed: %s [Req: %s]", e, req_id)
        flash(f"Error provisioning account. (Reference: {req_id})", "danger")

    return redirect(request.referrer or url_for('admin.admin_dashboard'))


@admin_bp.route('/edit_staff', methods=['POST'])
@login_required
def admin_edit_staff():
    """B-15: Edit admin staff with email uniqueness validation."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    staff_id = request.form.get('staff_id')
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()

    if not staff_id or not username or not email:
        flash("Username and email cannot be empty.", "warning")
        return redirect(url_for('admin.admin_staff'))

    u = db.session.get(User, int(staff_id))
    if u and u.usertype == 'Admin':
        # Uniqueness check
        existing = User.query.filter(User.email == email, User.id != u.id).first()
        if existing:
            flash(f"The email '{email}' is already in use by another account.", "danger")
            return redirect(url_for('admin.admin_staff'))

        u.username = username
        u.email = email
        db.session.commit()
        flash(f'Administrator {username} updated successfully.', 'success')

    return redirect(url_for('admin.admin_staff'))


@admin_bp.route('/change_staff_password', methods=['POST'])
@login_required
def admin_change_staff_password():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    staff_id = request.form.get('staff_id')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not new_password or len(new_password) < 8:
        flash('Password must be at least 8 characters long.', 'warning')
        return redirect(url_for('admin.admin_staff'))

    if new_password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('admin.admin_staff'))

    u = db.session.get(User, int(staff_id))
    if u and u.usertype == 'Admin':
        u.set_password(new_password)
        db.session.commit()
        flash('Administrator password updated successfully.', 'success')

    return redirect(url_for('admin.admin_staff'))


@admin_bp.route('/delete_staff', methods=['POST'])
@login_required
def admin_delete_staff():
    """B-19: Soft-deactivate admin user instead of hard delete."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    staff_id = request.form.get('staff_id')
    if int(staff_id) == current_user.id:
        flash('Safety Protocol: You cannot deactivate your own active session.', 'warning')
        return redirect(url_for('admin.admin_staff'))

    u = db.session.get(User, int(staff_id))
    if u and u.usertype == 'Admin':
        AccountsService.deactivate_user(u.id, actor=current_user)
        flash(f'Administrator {u.username} deactivated successfully.', 'success')

    return redirect(url_for('admin.admin_staff'))


# ── DOCTORS DIRECTORY ─────────────────────────────────────────────────

@admin_bp.route('/doctors')
@login_required
def admin_doctors():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    doctors = Doctor.query.options(joinedload(Doctor.user), joinedload(Doctor.department)).filter_by(is_active=True).all()
    doctors_list = []
    for doc in doctors:
        dept_name = doc.department.name if doc.department else (doc.dept or 'Unassigned')
        doctors_list.append({
            'id': doc.user_id,
            'doctor_id': doc.id,
            'username': doc.user.username if doc.user else 'Unknown',
            'email': doc.user.email if doc.user else '',
            'dept': dept_name,
            'fee': doc.consultation_fee
        })

    return render_template('admin/admin_doctors.html', doctors=doctors_list)


@admin_bp.route('/edit_doctor', methods=['POST'])
@login_required
def admin_edit_doctor():
    """B-14 & B-15: Edit doctor details with email uniqueness check."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    user_id = request.form.get('doctor_id')
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    dept = request.form.get('dept', '').strip()

    if not user_id or not username or not email:
        flash("Doctor username and email cannot be empty.", "warning")
        return redirect(url_for('admin.admin_doctors'))

    u = db.session.get(User, int(user_id))
    if u and u.usertype == 'Doctor':
        existing = User.query.filter(User.email == email, User.id != u.id).first()
        if existing:
            flash(f"The email '{email}' is already in use.", "danger")
            return redirect(url_for('admin.admin_doctors'))

        u.username = username
        u.email = email

        doc = Doctor.query.filter_by(user_id=u.id).first()
        if doc and dept:
            department = Department.query.filter_by(name=dept).first()
            if not department:
                department = Department(name=dept, code=dept[:4].upper())
                db.session.add(department)
                db.session.flush()
            doc.department_id = department.id
            doc.dept = dept

        db.session.commit()
        flash(f'Doctor {username} details updated successfully.', 'success')

    return redirect(url_for('admin.admin_doctors'))


@admin_bp.route('/change_doctor_password', methods=['POST'])
@login_required
def admin_change_doctor_password():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    doctor_id = request.form.get('doctor_id')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not new_password or len(new_password) < 8:
        flash('Password must be at least 8 characters long.', 'warning')
        return redirect(url_for('admin.admin_doctors'))

    if new_password != confirm_password:
        flash('Passwords do not match. Please try again.', 'danger')
        return redirect(url_for('admin.admin_doctors'))

    u = db.session.get(User, int(doctor_id))
    if u and u.usertype == 'Doctor':
        u.set_password(new_password)
        db.session.commit()
        flash('Doctor password updated successfully.', 'success')

    return redirect(url_for('admin.admin_doctors'))


@admin_bp.route('/delete_doctor', methods=['POST'])
@login_required
def admin_delete_doctor():
    """B-19: Soft-deactivate doctor account instead of hard deleting records."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    doctor_id = request.form.get('doctor_id')
    u = db.session.get(User, int(doctor_id))
    if u and u.usertype == 'Doctor':
        AccountsService.deactivate_user(u.id, actor=current_user)
        flash(f'Doctor account for {u.username} has been deactivated.', 'success')

    return redirect(url_for('admin.admin_doctors'))


# ── PATIENTS DIRECTORY ────────────────────────────────────────────────

@admin_bp.route('/patients')
@login_required
def admin_patients():
    """B-20: Patient directory with single aggregated appointment count query."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    search_query = request.args.get('search', '').strip()
    query = User.query.filter_by(usertype='Patient', is_active=True)

    if search_query:
        search_term = f'%{search_query}%'
        query = query.filter((User.username.ilike(search_term)) | (User.email.ilike(search_term)))

    patients = query.all()

    # B-20: Pre-compute counts in a single group-by query
    counts = dict(
        db.session.query(Appointment.patient_id, db.func.count(Appointment.id))
        .filter(Appointment.is_active.is_(True))
        .group_by(Appointment.patient_id)
        .all()
    )

    patients_list = []
    for p in patients:
        patients_list.append({
            'id': p.id,
            'username': p.username,
            'email': p.email,
            'phone': p.phone,
            'gender': p.gender,
            'appointment_count': counts.get(p.id, 0)
        })

    return render_template('admin/admin_patients.html', patients=patients_list, search_query=search_query)


# ── APPOINTMENTS ──────────────────────────────────────────────────────

@admin_bp.route('/appointments')
@login_required
def admin_appointments():
    """B-09 & B-20: Appointments list with relational sorting on starts_at and joinedload."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    today_str = date.today().isoformat()
    search_query = request.args.get('search', '').strip()
    default_date = 'all' if search_query else today_str

    selected_date = request.args.get('date', default_date)
    selected_doctor = request.args.get('doctor_id', '')

    q = Appointment.query.options(
        joinedload(Appointment.patient),
        joinedload(Appointment.doctor_rel).joinedload(Doctor.user),
        joinedload(Appointment.department)
    ).filter(Appointment.is_active.is_(True))

    if selected_date and selected_date != 'all':
        try:
            d = datetime.strptime(selected_date, '%Y-%m-%d').date()
            d_start = datetime.combine(d, datetime.min.time())
            d_end = datetime.combine(d, datetime.max.time())
            q = q.filter(Appointment.starts_at >= d_start, Appointment.starts_at <= d_end)
        except ValueError:
            pass

    if selected_doctor and selected_doctor.isdigit():
        q = q.filter(Appointment.doctor_id == int(selected_doctor))

    if search_query:
        search_term = f'%{search_query}%'
        q = q.join(User, Appointment.patient_id == User.id).filter(
            (User.username.ilike(search_term)) | (User.email.ilike(search_term))
        )

    # B-09: Order chronologically by starts_at datetime
    appts = q.order_by(Appointment.starts_at.desc()).all()

    appt_data = []
    for a in appts:
        status = 'Pending' if a.status == AppointmentStatus.SCHEDULED else a.status
        doc_user = a.doctor_rel.user if a.doctor_rel else None
        doc_name = doc_user.username if doc_user else 'Physician'
        dept_name = a.department.name if a.department else (a.doctor_rel.dept if a.doctor_rel else 'General')

        appt_data.append({
            'id': a.id,
            'patient_name': a.patient.username if a.patient else 'Unknown',
            'patient_email': a.patient.email if a.patient else 'Unknown',
            'doctor_name': doc_name,
            'dept': dept_name,
            'appointment_date': a.starts_at.strftime('%Y-%m-%d'),
            'time_slot': a.starts_at.strftime('%I:%M %p'),
            'status': status
        })

    doctors = Doctor.query.options(joinedload(Doctor.user), joinedload(Doctor.department)).filter_by(is_active=True).all()
    doctors_list = [
        {
            'id': doc.id,
            'username': doc.user.username if doc.user else 'Physician',
            'dept': doc.department.name if doc.department else (doc.dept or 'General')
        }
        for doc in doctors
    ]

    return render_template('admin/admin_appointments.html',
                           appts=appt_data,
                           doctors=doctors_list,
                           selected_date=selected_date,
                           selected_doctor=selected_doctor,
                           search_query=search_query)


@admin_bp.route('/update_appointment_status', methods=['POST'])
@login_required
def admin_update_appointment_status():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    appointment_id = request.form.get('appointment_id')
    status = request.form.get('status')
    redirect_url = request.form.get('redirect_url', url_for('admin.admin_appointments'))

    if status == 'Pending':
        status = AppointmentStatus.SCHEDULED

    a = db.session.get(Appointment, int(appointment_id))
    if a:
        a.status = status
        db.session.commit()
        flash('Appointment status updated successfully.', 'success')

    return redirect(redirect_url)


@admin_bp.route('/delete_appointment', methods=['POST'])
@login_required
def admin_delete_appointment():
    """B-19: Soft-deactivate appointment instead of hard delete."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    appointment_id = request.form.get('appointment_id')
    redirect_url = request.form.get('redirect_url', url_for('admin.admin_appointments'))

    a = db.session.get(Appointment, int(appointment_id))
    if a:
        a.is_active = False
        a.status = AppointmentStatus.CANCELLED
        a.deleted_at = datetime.now(UTC)
        db.session.commit()

        AuditService.record(
            action='APPOINTMENT_DEACTIVATED',
            entity_type='Appointment',
            entity_id=a.id,
            actor=current_user
        )
        flash('Appointment deactivated and archived successfully.', 'info')

    return redirect(redirect_url)


# ── FINANCIALS & BILLING ──────────────────────────────────────────────

@admin_bp.route('/financials')
@login_required
def admin_financials():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    all_invoices = Invoice.query.options(joinedload(Invoice.patient)).order_by(Invoice.issued_at.desc()).all()

    total_collected = sum((inv.total for inv in all_invoices if inv.status == 'Paid'), Decimal('0.00'))
    pending_revenue = sum((inv.total for inv in all_invoices if inv.status != 'Paid'), Decimal('0.00'))

    return render_template('admin/admin_financials.html',
                           bills=all_invoices,
                           total_collected=total_collected,
                           pending_revenue=pending_revenue)


@admin_bp.route('/financials/<int:bill_id>/invoice')
@login_required
def view_invoice(bill_id):
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    invoice = db.session.get(Invoice, bill_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('admin.admin_financials'))

    return render_template('admin/admin_view_invoice.html', invoice=invoice)


@admin_bp.route('/financials/<int:bill_id>/receipt')
@login_required
def view_receipt(bill_id):
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    invoice = db.session.get(Invoice, bill_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('admin.admin_financials'))

    return render_template('bookings/receipt.html', invoice=invoice)


# ── ROOM & WARD MANAGEMENT ────────────────────────────────────────────

@admin_bp.route('/rooms')
@login_required
def admin_rooms():
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    all_rooms = Room.query.filter_by(is_active=True).order_by(Room.room_number).all()
    active_admissions = Admission.query.options(
        joinedload(Admission.patient),
        joinedload(Admission.doctor).joinedload(Doctor.user),
        joinedload(Admission.room)
    ).filter_by(status=AdmissionStatus.ADMITTED).order_by(Admission.admission_date.desc()).all()

    total_rooms = len(all_rooms)
    available_rooms = sum(1 for r in all_rooms if r.status == RoomStatus.AVAILABLE)
    occupied_rooms = sum(1 for r in all_rooms if r.status == RoomStatus.OCCUPIED)
    maintenance_rooms = sum(1 for r in all_rooms if r.status == RoomStatus.MAINTENANCE)

    return render_template('admin/admin_rooms.html',
                           rooms=all_rooms,
                           active_admissions=active_admissions,
                           total_rooms=total_rooms,
                           available_rooms=available_rooms,
                           occupied_rooms=occupied_rooms,
                           maintenance_rooms=maintenance_rooms)


@admin_bp.route('/add_room', methods=['POST'])
@login_required
def add_room():
    """B-16: Safe input validation for room creation."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    room_number = (request.form.get('room_number') or '').strip()
    ward_type = (request.form.get('ward_type') or '').strip()
    rate_str = (request.form.get('rate_per_day') or '').strip()

    if not room_number or not ward_type or not rate_str:
        flash("All room fields are required.", "warning")
        return redirect(url_for('admin.admin_rooms'))

    if ward_type not in ALLOWED_WARD_TYPES:
        flash(f"Invalid ward type. Choose from: {', '.join(ALLOWED_WARD_TYPES)}", "danger")
        return redirect(url_for('admin.admin_rooms'))

    try:
        rate = Decimal(rate_str)
        if rate <= Decimal('0.00'):
            raise ValueError("Rate must be positive")
    except (InvalidOperation, ValueError):
        flash("Daily rate must be a valid positive number.", "danger")
        return redirect(url_for('admin.admin_rooms'))

    if Room.query.filter_by(room_number=room_number, is_active=True).first():
        flash(f"Room {room_number} already exists in the system.", "danger")
        return redirect(url_for('admin.admin_rooms'))

    new_room = Room(room_number=room_number, ward_type=ward_type, rate_per_day=rate)
    db.session.add(new_room)
    db.session.commit()

    AuditService.record(
        action='ROOM_CREATED',
        entity_type='Room',
        entity_id=new_room.id,
        actor=current_user,
        after={'room_number': room_number, 'ward': ward_type, 'rate': str(rate)}
    )

    flash(f"Room {room_number} successfully added to the {ward_type} ward.", "success")
    return redirect(url_for('admin.admin_rooms'))


@admin_bp.route('/edit_room', methods=['POST'])
@login_required
def edit_room():
    """B-16: Safe input validation for editing rooms."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    room_id = request.form.get('room_id')
    room = db.session.get(Room, int(room_id)) if room_id and room_id.isdigit() else None
    if not room:
        flash("Room not found.", "danger")
        return redirect(url_for('admin.admin_rooms'))

    room_number = (request.form.get('room_number') or '').strip()
    ward_type = (request.form.get('ward_type') or '').strip()
    rate_str = (request.form.get('rate_per_day') or '').strip()
    new_status = (request.form.get('status') or '').strip()

    if ward_type and ward_type in ALLOWED_WARD_TYPES:
        room.ward_type = ward_type

    if room_number:
        room.room_number = room_number

    if rate_str:
        try:
            rate = Decimal(rate_str)
            if rate > Decimal('0.00'):
                room.rate_per_day = rate
        except (InvalidOperation, ValueError):
            pass

    if new_status in RoomStatus.ALL:
        if room.status == RoomStatus.OCCUPIED and new_status != RoomStatus.OCCUPIED:
            flash(f"Cannot manually change status of Room {room.room_number}. It must be freed by a patient discharge.", "warning")
        else:
            room.status = new_status

    db.session.commit()
    flash(f"Room {room.room_number} details updated.", "success")
    return redirect(url_for('admin.admin_rooms'))


@admin_bp.route('/delete_room', methods=['POST'])
@login_required
def delete_room():
    """B-19: Soft-deactivate room instead of hard delete."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    room_id = request.form.get('room_id')
    room = db.session.get(Room, int(room_id)) if room_id and room_id.isdigit() else None
    if not room:
        flash("Room not found.", "danger")
        return redirect(url_for('admin.admin_rooms'))

    if room.status == RoomStatus.OCCUPIED:
        flash(f"Cannot delete Room {room.room_number} because a patient is currently admitted there.", "danger")
        return redirect(url_for('admin.admin_rooms'))

    room.is_active = False
    room.deleted_at = datetime.now(UTC)
    db.session.commit()

    AuditService.record(
        action='ROOM_DEACTIVATED',
        entity_type='Room',
        entity_id=room.id,
        actor=current_user
    )

    flash(f"Room {room.room_number} has been archived from active service.", "success")
    return redirect(url_for('admin.admin_rooms'))


@admin_bp.route('/discharge', methods=['POST'])
@admin_bp.route('/discharge/<int:admission_id>', methods=['POST'])
@login_required
def discharge_patient(admission_id=None):
    """Consolidated discharge & final billing (B-06, B-07)."""
    if current_user.usertype != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    if not admission_id:
        admission_id = request.form.get('admission_id')

    try:
        admission = AdmissionService.discharge(int(admission_id), actor=current_user)
        room_name = admission.room.room_number if admission.room else ''
        flash(f"Patient {admission.patient.username} has been officially discharged. Final invoice generated and Room {room_name} is now Available.", "success")
    except AdmissionError as e:
        flash(str(e), "danger")
    except Exception as e:
        req_id = getattr(g, 'request_id', 'ERR')
        current_app.logger.exception("Admin discharge failed: %s [Req: %s]", e, req_id)
        flash(f"Discharge error. (Reference: {req_id})", "danger")

    return redirect(url_for('admin.admin_rooms'))
