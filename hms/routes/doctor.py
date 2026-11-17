# routes/doctor.py
from decimal import Decimal

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

from hms.extensions import db
from hms.models.admission import Admission, AdmissionStatus, Room, RoomStatus
from hms.models.appointment import Appointment
from hms.models.billing import Invoice
from hms.models.doctor import Doctor
from hms.models.record import MedicalRecord
from hms.policies import can_edit_medical_record, can_view_medical_record
from hms.services.admissions import AdmissionError, AdmissionService, RoomNotAvailableError
from hms.services.appointments import (
    AppointmentService,
    InvalidStateTransitionError,
    UnauthorizedAppointmentActionError,
)
from hms.services.billing import BillingService
from hms.services.records import RecordError, RecordService

doctor_bp = Blueprint('doctor', __name__)


@doctor_bp.route('/cancel_apt/<int:apt_id>', methods=['POST'])
@login_required
def cancel_apt(apt_id):
    """Cancel an appointment with ownership verification (B-14, B-17, S-05)."""
    appointment = db.session.get(Appointment, apt_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('main.index'))

    doc_profile = Doctor.query.filter_by(user_id=current_user.id).first()
    if current_user.usertype != "Admin" and (not doc_profile or appointment.doctor_id != doc_profile.id):
        abort(403)

    try:
        AppointmentService.cancel(apt_id, actor=current_user, reason="Cancelled via schedule view")
        flash("Appointment has been successfully cancelled.", "warning")
    except UnauthorizedAppointmentActionError:
        abort(403)
    except InvalidStateTransitionError as e:
        flash(str(e), "warning")
    except Exception as e:
        req_id = getattr(g, 'request_id', 'ERR')
        current_app.logger.exception("Cancellation failed: %s [Req: %s]", e, req_id)
        flash(f"Could not cancel appointment. (Ref: {req_id})", "danger")

    return redirect(request.referrer or url_for('patient.dashboard'))


@doctor_bp.route('/mark_missed/<int:apt_id>', methods=['POST'])
@login_required
def mark_missed(apt_id):
    """Mark appointment missed with doctor ownership verification (B-14, B-17, S-05)."""
    if current_user.usertype != "Doctor":
        abort(403)

    doc_profile = Doctor.query.filter_by(user_id=current_user.id).first()
    appointment = db.session.get(Appointment, apt_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('main.index'))

    if not doc_profile or appointment.doctor_id != doc_profile.id:
        abort(403)

    try:
        AppointmentService.mark_missed(apt_id, actor=current_user)
        flash("Appointment marked as Missed.", "info")
    except Exception as e:
        flash(f"Error marking missed: {e}", "danger")

    return redirect(request.referrer or url_for('main.index'))


@doctor_bp.route('/mark_attended/<int:apt_id>', methods=['POST'])
@login_required
def mark_attended(apt_id):
    """Check in patient with doctor ownership verification (B-14, B-17, S-05)."""
    if current_user.usertype != "Doctor":
        abort(403)

    doc_profile = Doctor.query.filter_by(user_id=current_user.id).first()
    appointment = db.session.get(Appointment, apt_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('main.index'))

    if not doc_profile or appointment.doctor_id != doc_profile.id:
        abort(403)

    try:
        AppointmentService.check_in(apt_id, actor=current_user)
        flash("Patient marked as Attended. Clinical chart is ready.", "success")
    except InvalidStateTransitionError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error updating appointment: {e}", "danger")

    return redirect(request.referrer or url_for('main.index'))


@doctor_bp.route('/add_record/<int:apt_id>', methods=['GET', 'POST'])
@login_required
def add_record(apt_id):
    """Add clinical chart / prescription and optionally admit (B-12, B-13, B-14, S-05)."""
    if current_user.usertype != "Doctor":
        abort(403)

    appointment = db.session.get(Appointment, apt_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('main.index'))

    doc_profile = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doc_profile or appointment.doctor_id != doc_profile.id:
        abort(403)
        flash("Doctor profile not found.", "danger")
        return redirect(url_for('main.index'))

    # B-12 / B-14: Ownership check
    if appointment.doctor_id != doc_profile.id:
        flash("Unauthorized! You are not the assigned doctor for this appointment.", "danger")
        return redirect(url_for('main.index'))

    existing_record = MedicalRecord.query.filter_by(appointment_id=apt_id).first()
    if existing_record:
        flash("A medical record already exists for this appointment.", "warning")
        return redirect(url_for('doctor.view_record', apt_id=apt_id))

    if request.method == "POST":
        diagnosis = request.form.get('diagnosis', '').strip()
        prescription = request.form.get('prescription', '').strip()
        notes = request.form.get('notes', '').strip()
        room_id = request.form.get('room_id')

        if not diagnosis:
            flash("Diagnosis overview is required.", "warning")
            available_rooms = Room.query.filter_by(status=RoomStatus.AVAILABLE).all()
            return render_template('records/add_record.html', appointment=appointment, available_rooms=available_rooms)

        try:
            # 1. Create versioned medical record
            RecordService.create_record(
                appointment_id=apt_id,
                diagnosis=diagnosis,
                prescription=prescription,
                notes=notes,
                actor=current_user
            )

            # 2. Inpatient Admission flow
            if room_id and room_id.isdigit():
                AdmissionService.admit(
                    patient_id=appointment.patient_id,
                    doctor_id=doc_profile.id,
                    room_id=int(room_id),
                    appointment_id=appointment.id,
                    tentative_days=int(request.form.get('tentative_days', 1)),
                    actor=current_user
                )
                AppointmentService.complete(apt_id, actor=current_user)
                flash("Record saved and Patient Admitted! Inpatient billing will generate upon discharge.", "success")
                return redirect(url_for('main.index'))

            # 3. Outpatient flow: Generate consultation invoice
            fee = doc_profile.consultation_fee or Decimal('500.00')
            BillingService.create_appointment_invoice(appointment, fee=fee, actor=current_user)
            AppointmentService.complete(apt_id, actor=current_user)
            flash("Medical record saved and consultation invoice generated successfully!", "success")
            return redirect(url_for('main.index'))

        except RoomNotAvailableError as e:
            flash(str(e), "warning")
            return redirect(url_for('doctor.add_record', apt_id=apt_id))
        except (RecordError, AdmissionError) as e:
            flash(str(e), "danger")
            return redirect(url_for('doctor.add_record', apt_id=apt_id))
        except Exception as e:
            req_id = getattr(g, 'request_id', 'ERR')
            current_app.logger.exception("add_record failed: %s [Req: %s]", e, req_id)
            flash(f"System Error saving clinical record. (Reference: {req_id})", "danger")
            return redirect(url_for('doctor.add_record', apt_id=apt_id))

    available_rooms = Room.query.filter_by(status=RoomStatus.AVAILABLE).all()
    return render_template('records/add_record.html', appointment=appointment, available_rooms=available_rooms)


@doctor_bp.route('/my_admissions')
@doctor_bp.route('/doctor_admissions')
@login_required
def my_admissions():
    """Doctor view of their active admitted patients (S-05)."""
    if current_user.usertype != "Doctor":
        abort(403)

    doc_profile = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doc_profile:
        return render_template('records/doctor_admissions.html', admissions=[])

    my_patients = Admission.query.filter_by(
        doctor_id=doc_profile.id,
        status=AdmissionStatus.ADMITTED
    ).all()

    return render_template('records/doctor_admissions.html', admissions=my_patients)


@doctor_bp.route('/discharge_patient', methods=['POST'])
@login_required
def discharge_patient():
    """Consolidated discharge & final billing (B-06, B-07, S-05)."""
    if current_user.usertype not in ("Doctor", "Admin"):
        abort(403)

    admission_id = request.form.get('admission_id')
    if not admission_id:
        flash("Missing admission ID.", "danger")
        return redirect(url_for('doctor.my_admissions'))

    try:
        admission = AdmissionService.discharge(int(admission_id), actor=current_user)
        inv = Invoice.query.filter_by(admission_id=admission.id).first()
        total_bill = inv.total if inv else Decimal('0.00')
        patient_name = admission.patient.username if admission.patient else "Patient"
        flash(f"{patient_name} discharged successfully! Final bill of ₹{total_bill} generated.", "success")
    except AdmissionError as e:
        flash(str(e), "danger")
    except Exception as e:
        req_id = getattr(g, 'request_id', 'ERR')
        current_app.logger.exception("Discharge failed: %s [Req: %s]", e, req_id)
        flash(f"Discharge error. (Reference: {req_id})", "danger")

    return redirect(url_for('doctor.my_admissions'))


@doctor_bp.route('/view_record/<int:apt_id>')
@login_required
def view_record(apt_id):
    """View clinical record with RBAC policy check (S-05, B-14)."""
    appointment = db.session.get(Appointment, apt_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('main.index'))

    record = MedicalRecord.query.filter_by(appointment_id=apt_id).first()

    if record and not can_view_medical_record(current_user, record):
        abort(403)

    if not record:
        flash("No medical record has been generated yet.", "info")
        return redirect(url_for('patient.past_records'))

    return render_template('records/view_record.html', appointment=appointment, record=record)


@doctor_bp.route('/edit_record/<int:apt_id>', methods=['GET', 'POST'])
@login_required
def edit_record(apt_id):
    """Amend clinical record with amendment history snapshot (D-10, B-14, S-05)."""
    if current_user.usertype != "Doctor":
        abort(403)

    appointment = db.session.get(Appointment, apt_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('main.index'))

    record = MedicalRecord.query.filter_by(appointment_id=apt_id).first()
    if not record:
        flash("No medical record exists to edit yet.", "warning")
        return redirect(url_for('doctor.add_record', apt_id=apt_id))

    if not can_edit_medical_record(current_user, record):
        abort(403)

    if request.method == "POST":
        diagnosis = request.form.get('diagnosis', '').strip()
        prescription = request.form.get('prescription', '').strip()
        notes = request.form.get('notes', '').strip()
        reason = request.form.get('amendment_reason', 'Clinical amendment').strip()

        try:
            RecordService.amend_record(
                record_id=record.id,
                diagnosis=diagnosis,
                notes=notes,
                prescription=prescription,
                reason=reason,
                actor=current_user
            )
            flash("Medical record amended successfully with historical revision logged!", "success")
            return redirect(url_for('patient.past_records'))
        except Exception as e:
            flash(f"Error amending record: {e}", "danger")

    return render_template('records/edit_record.html', appointment=appointment, record=record)
