from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user

def require_roles(*roles):
    """
    Role-Based Access Control decorator.
    Verifies that the current authenticated user belongs to one of the authorized roles.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            
            user_type = getattr(current_user, 'usertype', None)
            if user_type not in roles:
                flash("Access Denied: You do not have permission to access this resource.", "danger")
                # Redirect to appropriate home page rather than crashing
                if user_type == 'Doctor':
                    return redirect(url_for('main.index'))
                elif user_type == 'Admin':
                    return redirect(url_for('admin.admin_dashboard'))
                elif user_type == 'Patient':
                    return redirect(url_for('patient.dashboard'))
                return redirect(url_for('main.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ── RESOURCE-LEVEL / OBJECT-LEVEL ACCESS POLICIES ────────────────────

def can_access_appointment(user, appointment):
    """Check if user is authorized to view this appointment."""
    if not user.is_authenticated:
        return False
    if user.usertype in ('Admin', 'Receptionist', 'Cashier'):
        return True
    if user.usertype == 'Doctor':
        # Check against username match or doctor profile did
        return appointment.doctor.strip().lower() == user.username.strip().lower()
    if user.usertype == 'Patient':
        return appointment.user_id == user.id
    return False

def can_modify_appointment_status(user, appointment):
    """Check if user is authorized to change appointment status (missed, attended, cancel)."""
    if not user.is_authenticated:
        return False
    if user.usertype in ('Admin', 'Receptionist'):
        return True
    if user.usertype == 'Doctor':
        return appointment.doctor.strip().lower() == user.username.strip().lower()
    return False

def can_chart_encounter(user, appointment):
    """Check if clinician is authorized to create/edit medical record for this appointment."""
    if not user.is_authenticated:
        return False
    if user.usertype == 'Admin':
        return True
    if user.usertype == 'Doctor':
        return appointment.doctor.strip().lower() == user.username.strip().lower()
    return False

def can_access_invoice(user, invoice):
    """Check if user is authorized to view this invoice or receipt."""
    if not user.is_authenticated:
        return False
    if user.usertype in ('Admin', 'Cashier', 'Receptionist'):
        return True
    if user.usertype == 'Patient':
        return invoice.user_id == user.id
    return False

def can_discharge_admission(user, admission):
    """Check if user is authorized to execute patient discharge."""
    if not user.is_authenticated:
        return False
    if user.usertype == 'Admin':
        return True
    if user.usertype == 'Doctor':
        doc_profile = getattr(user, 'doctor_profile', None)
        if doc_profile and doc_profile.did == admission.doctor_id:
            return True
        # Also check doctor username if profile not loaded
        if admission.doctor and admission.doctor.user_account and admission.doctor.user_account.id == user.id:
            return True
    return False
