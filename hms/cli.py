import os
import random
import secrets
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import click
from faker import Faker
from werkzeug.security import generate_password_hash

from hms.models import (
    Admission,
    AdmissionStatus,
    Appointment,
    AppointmentStatus,
    Department,
    Doctor,
    DoctorSchedule,
    HospitalSetting,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    MedicalRecord,
    NotificationOutbox,
    PatientProfile,
    Payment,
    PaymentMethod,
    PaymentStatus,
    PrescriptionItem,
    Room,
    RoomStatus,
    User,
    UserRole,
    db,
)
from hms.services.appointments import AppointmentService
from hms.services.notifications import NotificationService


def register_cli(app):
    """Register CLI commands with the Flask application."""

    @app.cli.command("create-admin")
    @click.option("--email", prompt="Admin Email", help="Email for the administrator")
    @click.option("--username", prompt="Admin Full Name", help="Full name of administrator")
    @click.password_option(prompt="Password", confirmation_prompt=True, help="Administrator password")
    def create_admin(email, username, password):
        """Create a new Administrator account interactively without echoing secrets."""
        email = email.strip().lower()
        username = username.strip()
        if len(password) < 10:
            click.secho("Error: Administrator password must be at least 10 characters.", fg="red")
            return

        with app.app_context():
            existing = User.query.filter_by(email=email).first()
            if existing:
                click.secho(f"Error: An account with email '{email}' already exists.", fg="red")
                return

            admin = User(
                username=username,
                usertype='Admin',
                email=email,
                password=generate_password_hash(password),
                phone='555-0100',
                gender='Male'
            )
            db.session.add(admin)
            db.session.commit()
            click.secho(f"Successfully created administrator: {username} ({email})", fg="green", bold=True)

    @app.cli.command("seed-demo")
    @click.option("--force", is_flag=True, help="Force reseed even if data exists")
    def seed_demo(force):
        """Seed realistic 6-month demo dataset using Faker (development only)."""
        app_env = os.environ.get('APP_ENV', 'development').lower()
        if app_env == 'production':
            click.secho("CRITICAL: seed-demo is blocked in production environment.", fg="red", bold=True)
            return

        with app.app_context():
            if not force and User.query.filter_by(usertype=UserRole.ADMIN).first():
                click.secho("Database already contains user records. Use --force to seed anyway.", fg="yellow")
                return

            fake = Faker('en_IN')
            Faker.seed(42)
            random.seed(42)

            admin_pwd = secrets.token_urlsafe(12)
            recep_pwd = secrets.token_urlsafe(12)
            doc_pwd = secrets.token_urlsafe(12)
            patient_pwd = secrets.token_urlsafe(12)

            # 1. Hospital Settings
            settings = [
                ("hospital_name", "Hedgewar Hospital Care", "Official hospital legal name"),
                ("emergency_phone", "+91 98500 64866", "24/7 Emergency and Trauma Helpline"),
                ("hospital_address", "Hedgewar Hospital Complex, Station Road, Chhatrapati Sambhajinagar, Maharashtra 431005", "Hospital address"),
                ("currency_symbol", "₹", "Display currency symbol"),
                ("consultation_cutoff_hours", "2", "Cancellation and reschedule cutoff window"),
            ]
            for k, v, desc in settings:
                if not HospitalSetting.query.filter_by(key=k).first():
                    db.session.add(HospitalSetting(key=k, value=v, description=desc))

            # 2. Departments
            dept_specs = [
                ("Cardiology", "CARD", "Specialized cardiovascular and coronary care"),
                ("Neurology", "NEUR", "Brain, spine, and central nervous system disorders"),
                ("Orthopedics", "ORTH", "Bone, joint, spine, and trauma surgery"),
                ("Pediatrics", "PEDS", "Newborn, child, and adolescent healthcare"),
                ("General Medicine", "GENM", "Comprehensive adult outpatient and inpatient care"),
                ("Dermatology", "DERM", "Skin, allergy, and cosmetic dermatology"),
            ]
            dept_map = {}
            for name, code, desc in dept_specs:
                dept = Department.query.filter_by(name=name).first()
                if not dept:
                    dept = Department(name=name, code=code, description=desc)
                    db.session.add(dept)
                    db.session.flush()
                dept_map[name] = dept

            # 3. Staff Accounts: Admin & Receptionist
            admin = User.query.filter_by(email="admin.demo@hedgewar.local").first()
            if not admin:
                admin = User(
                    username="Admin Executive",
                    usertype=UserRole.ADMIN,
                    email="admin.demo@hedgewar.local",
                    password=generate_password_hash(admin_pwd),
                    phone="+91 98200 00100",
                    gender="Male"
                )
                db.session.add(admin)

            recep = User.query.filter_by(email="receptionist.demo@hedgewar.local").first()
            if not recep:
                recep = User(
                    username="Front Desk Reception",
                    usertype=UserRole.RECEPTIONIST,
                    email="receptionist.demo@hedgewar.local",
                    password=generate_password_hash(recep_pwd),
                    phone="+91 98200 00101",
                    gender="Female"
                )
                db.session.add(recep)

            # 4. Doctors
            doctor_profiles_spec = [
                ("Dr. Mayur Sharma", "dr.sharma@hedgewar.local", "Cardiology", "MBBS, MD, DM (Cardiology)", Decimal("800.00"), 14),
                ("Dr. Priya Patel", "dr.patel@hedgewar.local", "Neurology", "MBBS, MD, DM (Neurology)", Decimal("900.00"), 12),
                ("Dr. Rajesh Deshmukh", "dr.deshmukh@hedgewar.local", "Orthopedics", "MBBS, MS (Ortho), MCh", Decimal("750.00"), 16),
                ("Dr. Ananya Kulkarni", "dr.kulkarni@hedgewar.local", "Pediatrics", "MBBS, MD (Pediatrics), DCH", Decimal("600.00"), 9),
                ("Dr. Vikram Joshi", "dr.joshi@hedgewar.local", "General Medicine", "MBBS, MD (Internal Medicine)", Decimal("500.00"), 18),
            ]
            doctors = []
            for name, email, dept_name, qual, fee, exp in doctor_profiles_spec:
                u = User.query.filter_by(email=email).first()
                if not u:
                    u = User(
                        username=name,
                        usertype=UserRole.DOCTOR,
                        email=email,
                        password=generate_password_hash(doc_pwd),
                        phone=fake.phone_number()[:15],
                        gender="Male" if "Mayur" in name or "Rajesh" in name or "Vikram" in name else "Female"
                    )
                    db.session.add(u)
                    db.session.flush()

                doc = Doctor.query.filter_by(user_id=u.id).first()
                if not doc:
                    doc = Doctor(
                        user_id=u.id,
                        department_id=dept_map[dept_name].id,
                        qualifications=qual,
                        consultation_fee=fee,
                        years_experience=exp,
                        bio=f"Senior consultant in {dept_name} at Hedgewar Hospital Care."
                    )
                    db.session.add(doc)
                    db.session.flush()

                    for day in range(5):
                        sched = DoctorSchedule(
                            doctor_id=doc.id,
                            weekday=day,
                            start_time=time(9, 0),
                            end_time=time(17, 0),
                            slot_minutes=30,
                            is_active=True
                        )
                        db.session.add(sched)
                doctors.append(doc)

            # 5. Inpatient Rooms
            room_specs = [
                ("101", "General", Decimal("800.00")),
                ("102", "General", Decimal("800.00")),
                ("103", "General", Decimal("800.00")),
                ("104", "General", Decimal("800.00")),
                ("201", "Semi-Private", Decimal("1500.00")),
                ("202", "Semi-Private", Decimal("1500.00")),
                ("301", "Private", Decimal("2500.00")),
                ("302", "Private", Decimal("2500.00")),
                ("ICU-1", "ICU", Decimal("5000.00")),
                ("ICU-2", "ICU", Decimal("5000.00")),
            ]
            rooms = []
            for r_num, w_type, rate in room_specs:
                r = Room.query.filter_by(room_number=r_num).first()
                if not r:
                    r = Room(room_number=r_num, ward_type=w_type, rate_per_day=rate, status=RoomStatus.AVAILABLE)
                    db.session.add(r)
                    db.session.flush()
                rooms.append(r)

            # 6. Patients & Profiles
            patients = []
            primary_p = User.query.filter_by(email="aarav.patient@hedgewar.local").first()
            if not primary_p:
                primary_p = User(
                    username="Aarav Sharma",
                    usertype=UserRole.PATIENT,
                    email="aarav.patient@hedgewar.local",
                    password=generate_password_hash(patient_pwd),
                    phone="+91 98300 00201",
                    gender="Male"
                )
                db.session.add(primary_p)
                db.session.flush()
                db.session.add(PatientProfile(
                    user_id=primary_p.id,
                    dob=date(1992, 5, 14),
                    blood_group="B+",
                    address="Flat 402, Shanti Enclave, Station Road, Chhatrapati Sambhajinagar",
                    emergency_contact_name="Sunita Sharma",
                    emergency_contact_phone="+91 98300 00202",
                    allergies="Penicillin",
                    chronic_conditions="Mild Asthma"
                ))
            patients.append(primary_p)

            blood_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
            for i in range(1, 21):
                p_email = f"patient{i}.demo@hedgewar.local"
                p_user = User.query.filter_by(email=p_email).first()
                if not p_user:
                    gender = "Male" if i % 2 == 0 else "Female"
                    p_user = User(
                        username=fake.name_male() if gender == "Male" else fake.name_female(),
                        usertype=UserRole.PATIENT,
                        email=p_email,
                        password=generate_password_hash(patient_pwd),
                        phone=fake.phone_number()[:15],
                        gender=gender
                    )
                    db.session.add(p_user)
                    db.session.flush()
                    db.session.add(PatientProfile(
                        user_id=p_user.id,
                        dob=date(random.randint(1955, 2005), random.randint(1, 12), random.randint(1, 28)),
                        blood_group=random.choice(blood_groups),
                        address=fake.address().replace("\n", ", "),
                        emergency_contact_name=fake.name(),
                        emergency_contact_phone=fake.phone_number()[:15],
                        allergies=random.choice(["None", "Sulfa drugs", "Dust", "Aspirin", "None"]),
                        chronic_conditions=random.choice(["None", "Type 2 Diabetes", "Hypertension", "None"])
                    ))
                patients.append(p_user)

            db.session.flush()

            # 7. Six Months of Historical Appointments & Clinical Records
            medicines_catalog = [
                ("Paracetamol 650mg", "1 tablet", "Three times daily after meals", "5 days", "For fever and pain"),
                ("Amoxicillin 500mg", "1 capsule", "Twice daily after food", "7 days", "Complete full antibiotic course"),
                ("Atorvastatin 10mg", "1 tablet", "Once daily at bedtime", "30 days", "Lipid control"),
                ("Metformin 500mg", "1 tablet", "Twice daily with meals", "30 days", "Blood glucose regulation"),
                ("Pantoprazole 40mg", "1 tablet", "Once daily before breakfast", "14 days", "Antacid"),
                ("Cetirizine 10mg", "1 tablet", "Once daily at night", "7 days", "Allergy relief"),
            ]
            diagnoses_pool = [
                ("Acute viral pharyngitis", "Patient presented with sore throat, mild fever, and malaise. Throat congested."),
                ("Essential hypertension review", "Routine BP follow-up. BP measured 138/88 mmHg. Systemic examination normal."),
                ("Type 2 diabetes mellitus routine review", "Fasting blood sugar 128 mg/dL. No microvascular complications noted."),
                ("Lumbar muscle strain", "Low back pain following heavy lifting. No neurological deficits on SLR test."),
                ("Mild acute gastroenteritis", "Nausea and watery stools since yesterday. Mild dehydration; hydrated in OPD."),
            ]

            now = datetime.now(UTC)
            inv_counter = 1000

            for d_idx in range(180, 0, -2):
                apt_date = now - timedelta(days=d_idx)
                slot_time = apt_date.replace(hour=10 + (d_idx % 6), minute=0, second=0, microsecond=0)
                doc = random.choice(doctors)
                patient = random.choice(patients)

                outcome = random.random()
                if outcome < 0.70:
                    status = AppointmentStatus.COMPLETED
                elif outcome < 0.85:
                    status = AppointmentStatus.CANCELLED
                else:
                    status = AppointmentStatus.MISSED

                apt = Appointment(
                    patient_id=patient.id,
                    doctor_id=doc.id,
                    department_id=doc.department_id,
                    starts_at=slot_time,
                    duration_min=30,
                    status=status,
                    reason="Routine consultation / follow-up",
                    cancelled_by=patient.id if status == AppointmentStatus.CANCELLED else None,
                    cancel_reason="Personal schedule conflict" if status == AppointmentStatus.CANCELLED else None
                )
                db.session.add(apt)
                db.session.flush()

                if status == AppointmentStatus.COMPLETED:
                    diag, notes = random.choice(diagnoses_pool)
                    rec = MedicalRecord(
                        appointment_id=apt.id,
                        patient_id=patient.id,
                        doctor_id=doc.id,
                        diagnosis=diag,
                        notes=notes,
                        prescription="Prescription issued digitally.",
                        version=1,
                        is_latest=True
                    )
                    db.session.add(rec)
                    db.session.flush()

                    for med_info in random.sample(medicines_catalog, 2):
                        db.session.add(PrescriptionItem(
                            record_id=rec.id,
                            medicine=med_info[0],
                            dose=med_info[1],
                            frequency=med_info[2],
                            duration=med_info[3],
                            instructions=med_info[4]
                        ))

                    inv_counter += 1
                    inv_num = f"INV-DEMO-{inv_counter}"
                    fee = doc.consultation_fee or Decimal("600.00")
                    inv = Invoice(
                        invoice_number=inv_num,
                        patient_id=patient.id,
                        appointment_id=apt.id,
                        status=InvoiceStatus.PAID,
                        issued_at=slot_time,
                        due_at=slot_time + timedelta(days=7),
                        subtotal=fee,
                        tax=Decimal("0.00"),
                        discount=Decimal("0.00"),
                        total=fee
                    )
                    db.session.add(inv)
                    db.session.flush()

                    db.session.add(InvoiceItem(
                        invoice_id=inv.id,
                        description=f"Consultation Fee - {doc.user.username}",
                        quantity=1,
                        unit_price=fee,
                        total_price=fee
                    ))

                    db.session.add(Payment(
                        invoice_id=inv.id,
                        method=random.choice([PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.UPI, PaymentMethod.MOCK]),
                        amount=fee,
                        status=PaymentStatus.SUCCESS,
                        paid_at=slot_time,
                        recorded_by=admin.id
                    ))

            # 8. Upcoming Appointments for Next 14 Days
            for day_offset in range(1, 14):
                if day_offset % 2 == 0:
                    continue
                future_time = (now + timedelta(days=day_offset)).replace(hour=11, minute=0, second=0, microsecond=0)
                db.session.add(Appointment(
                    patient_id=random.choice(patients).id,
                    doctor_id=doctors[day_offset % len(doctors)].id,
                    department_id=doctors[day_offset % len(doctors)].department_id,
                    starts_at=future_time,
                    duration_min=30,
                    status=AppointmentStatus.SCHEDULED,
                    reason="Scheduled health examination"
                ))

            # 9. Inpatient Admissions: Past Discharged & Active
            for adm_idx in range(6):
                p = patients[adm_idx + 1]
                doc = doctors[adm_idx % len(doctors)]
                room = rooms[adm_idx % len(rooms)]
                days_stay = random.randint(2, 5)
                adm_time = now - timedelta(days=30 + (adm_idx * 15))
                disch_time = adm_time + timedelta(days=days_stay)

                adm = Admission(
                    patient_id=p.id,
                    doctor_id=doc.id,
                    room_id=room.id,
                    admission_date=adm_time,
                    discharge_date=disch_time,
                    tentative_days=days_stay,
                    status=AdmissionStatus.DISCHARGED,
                    discharge_notes="Patient recovered satisfactorily. Discharged with oral medications."
                )
                db.session.add(adm)
                db.session.flush()

                inv_counter += 1
                room_total = room.rate_per_day * Decimal(str(days_stay))
                adm_inv = Invoice(
                    invoice_number=f"INV-ADM-{inv_counter}",
                    patient_id=p.id,
                    admission_id=adm.id,
                    status=InvoiceStatus.PAID,
                    issued_at=disch_time,
                    due_at=disch_time + timedelta(days=3),
                    subtotal=room_total,
                    tax=Decimal("0.00"),
                    discount=Decimal("0.00"),
                    total=room_total
                )
                db.session.add(adm_inv)
                db.session.flush()

                db.session.add(InvoiceItem(
                    invoice_id=adm_inv.id,
                    description=f"Inpatient Stay ({room.ward_type} Room {room.room_number}) - {days_stay} Days",
                    quantity=days_stay,
                    unit_price=room.rate_per_day,
                    total_price=room_total
                ))

                db.session.add(Payment(
                    invoice_id=adm_inv.id,
                    method=PaymentMethod.UPI,
                    amount=room_total,
                    status=PaymentStatus.SUCCESS,
                    paid_at=disch_time,
                    recorded_by=admin.id
                ))

            # Active Inpatient Admissions (Rooms 101, 201)
            active_rooms = [rooms[0], rooms[4]]
            for idx, a_room in enumerate(active_rooms):
                p = patients[15 + idx]
                doc = doctors[idx]
                a_room.status = RoomStatus.OCCUPIED
                db.session.add(Admission(
                    patient_id=p.id,
                    doctor_id=doc.id,
                    room_id=a_room.id,
                    admission_date=now - timedelta(days=2),
                    tentative_days=4,
                    status=AdmissionStatus.ADMITTED
                ))

            db.session.commit()

            click.secho("\n==================================================================", fg="cyan", bold=True)
            click.secho("  HEDGEWAR HOSPITAL CARE — 6-MONTH DEMO DATASET SEEDED", fg="cyan", bold=True)
            click.secho("==================================================================", fg="cyan")
            click.echo("Dev-only credentials (randomly generated, printed once):\n")
            click.echo(f"  Administrator : admin.demo@hedgewar.local        /  {admin_pwd}")
            click.echo(f"  Receptionist  : receptionist.demo@hedgewar.local /  {recep_pwd}")
            click.echo(f"  Doctor (Card) : dr.sharma@hedgewar.local         /  {doc_pwd}")
            click.echo(f"  Doctor (Neuro): dr.patel@hedgewar.local          /  {doc_pwd}")
            click.echo(f"  Patient (Demo): aarav.patient@hedgewar.local     /  {patient_pwd}\n")
            click.echo(f"  Total Users   : {User.query.count()} (1 Admin, 1 Receptionist, 5 Doctors, 21 Patients)")
            click.echo(f"  Appointments  : {Appointment.query.count()} across past 180 days and next 14 days")
            click.echo(f"  Admissions    : {Admission.query.count()} (6 Discharged, 2 Currently Admitted)")
            click.echo(f"  Invoices      : {Invoice.query.count()} fully itemized with settled payments")
            click.secho("==================================================================\n", fg="cyan")

    @app.cli.command("mark-missed")
    @click.option("--grace-minutes", default=60, help="Grace minutes after scheduled start before marking Missed")
    def mark_missed(grace_minutes):
        """Automatically transition past unattended appointments to Missed (R-04)."""
        with app.app_context():
            cutoff = datetime.now() - timedelta(minutes=grace_minutes)
            past_due = Appointment.query.filter(
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.starts_at < cutoff,
                Appointment.is_active.is_(True)
            ).all()
            count = 0
            for apt in past_due:
                try:
                    AppointmentService.mark_missed(apt.id)
                    count += 1
                except Exception as e:
                    click.secho(f"Warning: Failed to mark appointment {apt.id} missed: {e}", fg="yellow")
            click.echo(f"Processed {count} missed appointments.")

    @app.cli.command("send-reminders")
    @click.option("--lead-hours", default=24, help="Advance notice hours for reminder (default 24h)")
    @click.option("--window-minutes", default=60, help="Search window tolerance in minutes (default +/- 60m)")
    def send_reminders(lead_hours, window_minutes):
        """Dispatch appointment reminder notifications idempotently (R-04)."""
        with app.app_context():
            target_time = datetime.now() + timedelta(hours=lead_hours)
            window_start = target_time - timedelta(minutes=window_minutes)
            window_end = target_time + timedelta(minutes=window_minutes)

            upcoming = Appointment.query.filter(
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.starts_at >= window_start,
                Appointment.starts_at <= window_end,
                Appointment.is_active.is_(True)
            ).all()

            sent = 0
            skipped = 0
            for apt in upcoming:
                # Idempotency check: verify if a reminder has already been queued
                existing = NotificationOutbox.query.filter(
                    NotificationOutbox.event_type == 'appointment_reminder',
                    NotificationOutbox.recipient == apt.patient.email,
                    NotificationOutbox.body.contains(f'#{apt.id}')
                ).first()

                if existing:
                    skipped += 1
                    continue

                try:
                    NotificationService.send_appointment_reminder(apt)
                    sent += 1
                except Exception as e:
                    click.secho(f"Warning: Failed to send reminder for appointment {apt.id}: {e}", fg="yellow")

            click.echo(f"Reminders processed: {sent} dispatched, {skipped} skipped (already queued).")

    @app.cli.command("run-scheduler")
    @click.option("--interval-reminders", default=900, help="Seconds between reminder checks (default 900s / 15m)")
    @click.option("--interval-missed", default=600, help="Seconds between missed checks (default 600s / 10m)")
    @click.option("--once", is_flag=True, help="Run one cycle of all scheduled jobs and exit")
    def run_scheduler(interval_reminders, interval_missed, once):
        """Run scheduled background jobs continuously or one-off (R-04)."""
        import time

        click.echo("Starting HMS Background Job Scheduler (R-04)...")
        click.echo(f"Config: Reminders every {interval_reminders}s, Mark-Missed every {interval_missed}s")

        last_reminders = 0.0
        last_missed = 0.0

        while True:
            now = time.time()
            if now - last_reminders >= interval_reminders or once:
                click.echo(f"[{datetime.now().isoformat()}] Running send-reminders...")
                send_reminders.callback(lead_hours=24, window_minutes=60)
                last_reminders = now

            if now - last_missed >= interval_missed or once:
                click.echo(f"[{datetime.now().isoformat()}] Running mark-missed...")
                mark_missed.callback(grace_minutes=60)
                last_missed = now

            if once:
                click.echo("Scheduler one-off run complete.")
                break

            time.sleep(10)
