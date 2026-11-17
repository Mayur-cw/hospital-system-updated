from datetime import date, datetime, time, timedelta
from typing import Any

from hms.models.appointment import Appointment, AppointmentStatus
from hms.models.availability import DoctorLeave, DoctorSchedule


class AvailabilityService:
    @staticmethod
    def get_available_slots(doctor_id: int, query_date: date) -> list[dict[str, Any]]:
        """
        Generate available appointment slots for a doctor on a given date (D-08).
        Subtracts leaves, breaks, and existing active bookings.
        """
        # 1. Check if doctor is on approved leave
        leave = DoctorLeave.query.filter(
            DoctorLeave.doctor_id == doctor_id,
            DoctorLeave.status == 'Approved',
            DoctorLeave.date_from <= query_date,
            DoctorLeave.date_to >= query_date
        ).first()

        if leave:
            return []

        # 2. Get schedule for the day of week (0=Mon, 6=Sun)
        weekday = query_date.weekday()
        schedule = DoctorSchedule.query.filter_by(
            doctor_id=doctor_id,
            weekday=weekday,
            is_active=True
        ).first()

        if schedule:
            start_time = schedule.start_time
            end_time = schedule.end_time
            slot_minutes = schedule.slot_minutes
            breaks = schedule.breaks
        else:
            # Default clinical schedule: 09:00 - 17:00, 30 min slots, lunch 13:00-14:00
            start_time = time(9, 0)
            end_time = time(17, 0)
            slot_minutes = 30
            breaks = [{'start_time': time(13, 0), 'end_time': time(14, 0)}]

        # 3. Query existing active appointments on query_date
        day_start = datetime.combine(query_date, time.min)
        day_end = datetime.combine(query_date, time.max)

        active_appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.starts_at >= day_start,
            Appointment.starts_at <= day_end,
            Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.MISSED]),
            Appointment.is_active.is_(True)
        ).all()

        booked_times = {apt.starts_at.strftime('%H:%M') for apt in active_appointments}

        # 4. Generate candidate time slots
        slots = []
        curr_dt = datetime.combine(query_date, start_time)
        end_dt = datetime.combine(query_date, end_time)
        step = timedelta(minutes=slot_minutes)

        now = datetime.now()

        while curr_dt < end_dt:
            slot_time = curr_dt.time()
            time_str = slot_time.strftime('%H:%M')

            # Check if in a break
            in_break = False
            for brk in breaks:
                b_start = getattr(brk, 'start_time', brk.get('start_time') if isinstance(brk, dict) else None)
                b_end = getattr(brk, 'end_time', brk.get('end_time') if isinstance(brk, dict) else None)
                if b_start and b_end and b_start <= slot_time < b_end:
                    in_break = True
                    break

            is_booked = time_str in booked_times
            is_past = (query_date < now.date()) or (query_date == now.date() and slot_time < now.time())

            if not in_break:
                slots.append({
                    'time': time_str,
                    'datetime': curr_dt.isoformat(),
                    'available': not is_booked and not is_past,
                    'status': 'Booked' if is_booked else ('Past' if is_past else 'Available')
                })

            curr_dt += step

        return slots
