from decimal import Decimal
from typing import Any

from werkzeug.security import generate_password_hash

from hms.extensions import db
from hms.models.department import Department
from hms.models.doctor import Doctor
from hms.models.patient import PatientProfile
from hms.models.user import User, UserRole
from hms.services.audit import AuditService


class AccountServiceError(Exception):
    pass

class EmailAlreadyExistsError(AccountServiceError):
    pass

class InvalidCredentialsError(AccountServiceError):
    pass

class AccountService:
    @staticmethod
    def create_user(username: str, email: str, password: str, usertype: str = UserRole.PATIENT,
                    phone: str | None = None, gender: str | None = None,
                    dept: str | None = None, actor=None) -> User:
        """Unified user creation helper."""
        if usertype == UserRole.PATIENT:
            return AccountService.create_patient(username, email, password, phone=phone, gender=gender, actor=actor)
        return AccountService.create_staff(username, email, password, usertype=usertype, dept_name=dept, actor=actor)

    @staticmethod
    def create_patient(username: str, email: str, password: str,
                       phone: str | None = None, gender: str | None = None,
                       profile_data: dict[str, Any] | None = None,
                       actor=None) -> User:
        """Register a new patient account."""
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            raise EmailAlreadyExistsError(f"An account with email {email} already exists.")

        user = User(
            username=username.strip(),
            email=email,
            password=generate_password_hash(password),
            usertype=UserRole.PATIENT,
            phone=phone.strip() if phone else None,
            gender=gender.strip() if gender else None
        )
        db.session.add(user)
        db.session.flush()

        profile = PatientProfile(
            user_id=user.id,
            dob=profile_data.get('dob') if profile_data else None,
            blood_group=profile_data.get('blood_group') if profile_data else None,
            address=profile_data.get('address') if profile_data else None,
            emergency_contact_name=profile_data.get('emergency_contact_name') if profile_data else None,
            emergency_contact_phone=profile_data.get('emergency_contact_phone') if profile_data else None,
            allergies=profile_data.get('allergies') if profile_data else None,
            chronic_conditions=profile_data.get('chronic_conditions') if profile_data else None
        )
        db.session.add(profile)
        db.session.commit()

        AuditService.record(
            action='USER_SIGNUP',
            entity_type='User',
            entity_id=user.id,
            actor=actor or user,
            after={'username': user.username, 'email': user.email, 'role': user.usertype}
        )
        return user

    @staticmethod
    def create_staff(username: str, email: str, password: str, usertype: str,
                     department_id: int | None = None, dept_name: str | None = None,
                     consultation_fee: Decimal = Decimal('500.00'),
                     qualifications: str | None = None,
                     actor=None) -> User:
        """Provision a staff account (Doctor, Admin, Receptionist)."""
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            raise EmailAlreadyExistsError(f"An account with email {email} already exists.")

        user = User(
            username=username.strip(),
            email=email,
            password=generate_password_hash(password),
            usertype=usertype
        )
        db.session.add(user)
        db.session.flush()

        if usertype == UserRole.DOCTOR:
            # Resolve department if dept_name is passed
            if not department_id and dept_name:
                dept = Department.query.filter_by(name=dept_name).first()
                if not dept:
                    dept = Department(name=dept_name, code=dept_name[:4].upper())
                    db.session.add(dept)
                    db.session.flush()
                department_id = dept.id

            doc = Doctor(
                user_id=user.id,
                department_id=department_id,
                consultation_fee=consultation_fee,
                qualifications=qualifications
            )
            db.session.add(doc)

        db.session.commit()

        AuditService.record(
            action='STAFF_PROVISIONED',
            entity_type='User',
            entity_id=user.id,
            actor=actor,
            after={'username': user.username, 'email': user.email, 'role': user.usertype}
        )
        return user

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str, actor=None) -> bool:
        """Change user password after verifying the current password."""
        if not user.check_password(current_password):
            raise InvalidCredentialsError("Current password does not match.")

        user.set_password(new_password)
        db.session.commit()

        AuditService.record(
            action='PASSWORD_CHANGED',
            entity_type='User',
            entity_id=user.id,
            actor=actor or user
        )
        return True

    @staticmethod
    def deactivate_user(user_id: int, actor=None) -> User:
        """Soft-deactivate a user (never hard delete clinical history)."""
        user = db.session.get(User, user_id)
        if not user:
            raise AccountServiceError("User not found.")

        user.soft_delete()
        db.session.commit()

        AuditService.record(
            action='USER_DEACTIVATED',
            entity_type='User',
            entity_id=user.id,
            actor=actor
        )
        return user


# Plural alias
AccountsService = AccountService
