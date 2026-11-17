import os
import secrets
import click
from werkzeug.security import generate_password_hash
from models import db, User, Doctors, Room

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
                click.secho("Demo data already present. Use --force to reseed.", fg="yellow")
                return

            click.secho("Seeding isolated demo hospital dataset with unique passwords...", fg="cyan")
            passwords = {
                'admin': secrets.token_urlsafe(12),
                'doctor1': secrets.token_urlsafe(12),
                'doctor2': secrets.token_urlsafe(12),
                'patient1': secrets.token_urlsafe(12),
                'patient2': secrets.token_urlsafe(12),
            }

            u_admin = User(
                username="Dr. Amit Mehta",
                usertype="Admin",
                email="admin@hospital.local",
                password=generate_password_hash(passwords['admin']),
                phone="555-0101",
                gender="Male"
            )
            u_doc1 = User(
                username="Dr. Rajesh Sharma",
                usertype="Doctor",
                email="dr.sharma@hospital.local",
                password=generate_password_hash(passwords['doctor1']),
                phone="555-0102",
                gender="Male"
            )
            u_doc2 = User(
                username="Dr. Ananya Patel",
                usertype="Doctor",
                email="dr.patel@hospital.local",
                password=generate_password_hash(passwords['doctor2']),
                phone="555-0103",
                gender="Female"
            )
            u_pat1 = User(
                username="Aarav Mehta",
                usertype="Patient",
                email="patient1@hospital.local",
                password=generate_password_hash(passwords['patient1']),
                phone="555-0201",
                gender="Male"
            )
            u_pat2 = User(
                username="Pooja Nair",
                usertype="Patient",
                email="patient2@hospital.local",
                password=generate_password_hash(passwords['patient2']),
                phone="555-0202",
                gender="Female"
            )
            db.session.add_all([u_admin, u_doc1, u_doc2, u_pat1, u_pat2])
            db.session.flush()

            d1 = Doctors(user_id=u_doc1.id, dept="Cardiologists")
            d2 = Doctors(user_id=u_doc2.id, dept="Dermatologists")
            db.session.add_all([d1, d2])

            r1 = Room(room_number="101", ward_type="General", rate_per_day=800.00, status="Available")
            r2 = Room(room_number="201", ward_type="ICU", rate_per_day=3500.00, status="Available")
            r3 = Room(room_number="301", ward_type="VIP", rate_per_day=5000.00, status="Available")
            db.session.add_all([r1, r2, r3])
            db.session.commit()

            click.secho("\n=======================================================", fg="green")
            click.secho(" DEMO DATA SEEDED SUCCESSFULLY (CREDENTIALS PRINTED ONCE)", fg="green", bold=True)
            click.secho("=======================================================", fg="green")
            click.echo(f"Admin:     {u_admin.email:<28} Password: {passwords['admin']}")
            click.echo(f"Doctor 1:  {u_doc1.email:<28} Password: {passwords['doctor1']}")
            click.echo(f"Doctor 2:  {u_doc2.email:<28} Password: {passwords['doctor2']}")
            click.echo(f"Patient 1: {u_pat1.email:<28} Password: {passwords['patient1']}")
            click.echo(f"Patient 2: {u_pat2.email:<28} Password: {passwords['patient2']}")
            click.secho("=======================================================\n", fg="green")
