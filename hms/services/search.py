from hms.models.appointment import Appointment
from hms.models.department import Department
from hms.models.doctor import Doctor
from hms.models.user import User


class SearchService:
    @staticmethod
    def global_search(query: str, current_user=None, search_type: str = "all") -> list[dict]:
        """
        Global typeahead search scoped by actor authorization (F-02).
        Returns a list of search matches with categories and destination URLs.
        """
        query = (query or "").strip().lower()
        if not query or len(query) < 2:
            return []

        results = []

        is_auth = current_user and getattr(current_user, 'is_authenticated', False)
        is_admin = is_auth and getattr(current_user, 'is_admin', False)
        is_doctor = is_auth and getattr(current_user, 'is_doctor', False)

        # 1. Search Doctors (accessible to everyone: Public, Patient, Staff)
        if search_type in ("all", "doctors"):
            doctors = Doctor.query.join(User, Doctor.user_id == User.id).outerjoin(
                Department, Doctor.department_id == Department.id
            ).filter(
                (User.username.ilike(f"%{query}%")) |
                (User.email.ilike(f"%{query}%")) |
                (Department.name.ilike(f"%{query}%")) |
                (Doctor.qualifications.ilike(f"%{query}%"))
            ).limit(10).all()

            for doc in doctors:
                dept_name = doc.department.name if doc.department else "General Practice"
                spec = f" · {doc.qualifications}" if doc.qualifications else ""
                results.append({
                    "category": "Doctor",
                    "title": f"Dr. {doc.user.username}",
                    "subtitle": f"{dept_name}{spec}",
                    "url": f"/doctors?dept={doc.department_id}" if doc.department_id else "/doctors"
                })

        # 2. Search Patients (staff only: Admins see all, Doctors see patients they treated)
        if search_type in ("all", "patients") and is_auth:
            if is_admin:
                patients = User.query.filter(
                    User.usertype == "Patient",
                    User.is_active.is_(True),
                    (User.username.ilike(f"%{query}%")) |
                    (User.email.ilike(f"%{query}%")) |
                    (User.phone.ilike(f"%{query}%"))
                ).limit(10).all()

                for p in patients:
                    results.append({
                        "category": "Patient",
                        "title": p.username,
                        "subtitle": f"{p.email} · PID-{p.id}",
                        "url": f"/admin/appointments?search={p.email}&date=all"
                    })

            elif is_doctor:
                doc_profile = getattr(current_user, 'doctor_profile', None)
                if doc_profile:
                    # Query appointments treated by this doctor
                    treated_patient_ids = [
                        apt.patient_id for apt in Appointment.query.filter_by(doctor_id=doc_profile.id).all()
                    ]
                    patients = User.query.filter(
                        User.id.in_(treated_patient_ids),
                        User.usertype == "Patient",
                        User.is_active.is_(True),
                        (User.username.ilike(f"%{query}%")) |
                        (User.email.ilike(f"%{query}%")) |
                        (User.phone.ilike(f"%{query}%"))
                    ).limit(10).all()

                    for p in patients:
                        results.append({
                            "category": "Patient",
                            "title": p.username,
                            "subtitle": f"{p.email} · PID-{p.id}",
                            "url": f"/doctor/queue?patient_id={p.id}"
                        })

        return results
