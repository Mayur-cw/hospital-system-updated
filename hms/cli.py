import os
import secrets
from datetime import datetime, timedelta

import click
from werkzeug.security import generate_password_hash

from hms.models import (
    Appointment,
    AppointmentStatus,
    Department,
    Doctor,
    NotificationOutbox,
    Room,
    User,
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
        """Seed non-production development demo data with randomized credentials."""
        app_env = os.environ.get('APP_ENV', 'development').lower()
        if app_env == 'production':
            click.secho("CRITICAL: seed-demo is blocked in production environment.", fg="red", bold=True)
            return

        with app.app_context():
            if not force and User.query.filter_by(usertype='Admin').first():
                click.secho("Database already contains user records. Use --force to seed anyway.", fg="yellow")
                return

            admin_pwd = secrets.token_urlsafe(12)
            doc1_pwd = secrets.token_urlsafe(12)
            doc2_pwd = secrets.token_urlsafe(12)
            patient_pwd = secrets.token_urlsafe(12)

            # Ensure Departments exist
            cardio = Department.query.filter_by(name='Cardiology').first()
            if not cardio:
                cardio = Department(name='Cardiology', code='CARD', description='Cardiovascular medicine')
                db.session.add(cardio)
            neuro = Department.query.filter_by(name='Neurology').first()
            if not neuro:
                neuro = Department(name='Neurology', code='NEUR', description='Neurological medicine')
                db.session.add(neuro)
            peds = Department.query.filter_by(name='Pediatrics').first()
            if not peds:
                peds = Department(name='Pediatrics', code='PEDS', description='Pediatric care')
                db.session.add(peds)
            db.session.flush()

            # Seed Admin
            admin = User(
                username="System Administrator",
                usertype="Admin",
                email="admin.demo@hedgewar.local",
                password=generate_password_hash(admin_pwd),
                phone="555-0100",
                gender="Male"
            )
            db.session.add(admin)

            # Seed Doctor 1
            doc1_user = User(
                username="Dr. Mayur Sharma",
                usertype="Doctor",
                email="dr.sharma@hedgewar.local",
                password=generate_password_hash(doc1_pwd),
                phone="555-0101",
                gender="Male"
            )
            db.session.add(doc1_user)
            db.session.flush()
            doc1 = Doctor(user_id=doc1_user.id, department_id=cardio.id, qualifications="MBBS, MD (Cardiology)")
            db.session.add(doc1)

            # Seed Doctor 2
            doc2_user = User(
                username="Dr. Priya Patel",
                usertype="Doctor",
                email="dr.patel@hedgewar.local",
                password=generate_password_hash(doc2_pwd),
                phone="555-0102",
                gender="Female"
            )
            db.session.add(doc2_user)
            db.session.flush()
            doc2 = Doctor(user_id=doc2_user.id, department_id=neuro.id, qualifications="MBBS, DM (Neurology)")
            db.session.add(doc2)

            # Seed Demo Patient
            patient = User(
                username="Aarav Sharma",
                usertype="Patient",
                email="aarav.patient@hedgewar.local",
                password=generate_password_hash(patient_pwd),
                phone="555-0201",
                gender="Male"
            )
            db.session.add(patient)

            # Seed Rooms
            room_specs = [
                ("101", "General", 800.00),
                ("102", "General", 800.00),
                ("201", "Semi-Private", 1500.00),
                ("301", "Private", 2500.00),
                ("ICU-1", "ICU", 5000.00),
            ]
            for r_num, w_type, rate in room_specs:
                if not Room.query.filter_by(room_number=r_num).first():
                    db.session.add(Room(room_number=r_num, ward_type=w_type, rate_per_day=rate, status='Available'))

            db.session.commit()

            click.secho("\n=======================================================", fg="cyan", bold=True)
            click.secho(" DEMO DATA SEEDED SUCCESSFULLY (DEVELOPMENT ONLY)", fg="cyan", bold=True)
            click.secho("=======================================================", fg="cyan")
            click.echo("Copy these temporary credentials (they are printed only once):\n")
            click.echo(f"  Admin:   admin.demo@hedgewar.local       /  {admin_pwd}")
            click.echo(f"  Doctor:  dr.sharma@hedgewar.local        /  {doc1_pwd}")
            click.echo(f"  Doctor:  dr.patel@hedgewar.local         /  {doc2_pwd}")
            click.echo(f"  Patient: aarav.patient@hedgewar.local    /  {patient_pwd}\n")
            click.secho("=======================================================\n", fg="cyan")

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
