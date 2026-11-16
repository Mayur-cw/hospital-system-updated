from datetime import datetime, date
from models import db, Appointments, AuditLog

class SchedulingService:
    @staticmethod
    def is_slot_available(doctor_name, date_str, time_str, exclude_apt_id=None):
        """Check if a doctor slot is available."""
        query = Appointments.query.filter_by(doctor=doctor_name, date=date_str, time=time_str)
        if exclude_apt_id:
            query = query.filter(Appointments.apt_id != exclude_apt_id)
        
        existing = query.all()
        active = [a for a in existing if a.slot not in ('Cancelled', 'Missed')]
        return len(active) == 0

    @staticmethod
    def book_appointment(user_id, doctor_name, dept, date_str, time_str, disease, slot='Scheduled'):
        """
        Concurrency-safe, atomic appointment booking service.
        Replaces the non-portable raw MySQL BookAppointmentSafe stored procedure.
        """
        try:
            apt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = date.today()
            if apt_date < today:
                return False, "Error: You cannot book an appointment in the past.", None
                
            if apt_date == today:
                apt_time = datetime.strptime(time_str, '%I:%M %p').time()
                curr_time = datetime.now().time()
                if apt_time < curr_time:
                    return False, "Error: That time slot has already passed today.", None
        except ValueError:
            return False, "Invalid date or time format.", None

        # Concurrency lock on existing slot
        try:
            # Check availability with row lock where supported
            existing_conflict = Appointments.query.filter(
                Appointments.doctor == doctor_name,
                Appointments.date == date_str,
                Appointments.time == time_str,
                Appointments.slot.notin_(['Cancelled', 'Missed'])
            ).with_for_update().first()
            
            if existing_conflict:
                return False, "Slot Unavailable: That time slot was just taken by another user. Please choose another slot.", None
                
            # Compute token number for this doctor on this day
            daily_count = Appointments.query.filter_by(doctor=doctor_name, date=date_str).count()
            token_num = daily_count + 1

            new_apt = Appointments(
                user_id=user_id,
                doctor=doctor_name,
                dept=dept,
                date=date_str,
                time=time_str,
                disease=disease,
                slot=slot,
                token_number=token_num
            )
            db.session.add(new_apt)
            db.session.flush() # Flush to generate apt_id

            # Add Audit Log
            audit = AuditLog(
                apt_id=new_apt.apt_id,
                user_id=user_id,
                action=f"APPOINTMENT BOOKED (Dr: {doctor_name}, Token: #{token_num})",
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            db.session.add(audit)
            db.session.commit()
            
            return True, "Appointment booked successfully!", new_apt

        except Exception as e:
            db.session.rollback()
            return False, f"Booking transaction failed: {str(e)}", None
