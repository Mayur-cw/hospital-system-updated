# Hospital Management System (HMS) - Render Deployment Guide

This project is fully configured for deployment on [Render](https://render.com).

---

## 🚀 Quick Deploy: Option 1 — Render Blueprint (Recommended)

1. Fork or push this repository to your GitHub account (already live at [https://github.com/Mayur-cw/hospital-system-updated](https://github.com/Mayur-cw/hospital-system-updated)).
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** > **Blueprint**.
4. Connect the **hospital-system-updated** repository.
5. Render will automatically detect [`render.yaml`](./render.yaml) and configure:
   - **Environment**: Python 3.12
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn wsgi:app`
   - **Environment Variables**: Automatic production-grade `SECRET_KEY` generation.
6. Click **Apply** to deploy.

---

## 🛠️ Quick Deploy: Option 2 — Manual Web Service Setup

If you prefer to create a standard Web Service directly:

1. Click **New +** > **Web Service**.
2. Connect your repository.
3. Configure settings:
   - **Name**: `hospital-management-system`
   - **Region**: Closest to your users (e.g., Singapore, Frankfurt, Oregon, Ohio)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn wsgi:app`
   - **Instance Type**: `Free`
4. Add the following **Environment Variables**:
   | Variable | Value | Description |
   | :--- | :--- | :--- |
   | `PYTHON_VERSION` | `3.12.14` | Specifies modern Python runtime |
   | `APP_ENV` | `production` | Enables production security & session cookies |
   | `DEMO_ONLY` | `true` | Allows synthetic demo accounts & test workflow |
   | `FLASK_DEBUG` | `false` | Disables debug mode in production |
   | `SECRET_KEY` | *(Generate a random 32+ char hex)* | Session & CSRF encryption key |
   | `DATABASE_URL` | *(Optional)* | Render PostgreSQL connection string |

5. Click **Deploy Web Service**.

---

## 🗄️ Database Options

### 1. Built-in SQLite Demo Database (Zero Setup)
If `DATABASE_URL` is omitted, the application uses the included pre-seeded SQLite database with full medical synthetic records.
*Note: Free tier Render instances have ephemeral disks; any newly created patients or appointments reset when the container spins down unless a persistent disk or PostgreSQL is attached.*

### 2. Managed Render PostgreSQL (Persistent & Production Ready)
1. In Render Dashboard, click **New +** > **PostgreSQL**.
2. Name it `hospital-db` and select the Free tier.
3. Copy the **Internal Database URL** (e.g., `postgres://user:password@dpg-.../hospital_db`).
4. In your Web Service settings, set `DATABASE_URL` to that value.
5. During build, `./build.sh` will automatically run `scripts/seed_synthetic.py` to populate tables and initial staff accounts.

---

## 🔑 Default Synthetic Login Credentials

| Role | Email | Password | Pre-loaded Context |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@hospital.local` | `AdminPass@2026` | Full Control Center, OPD Queue, Staff & Bed Management |
| **Specialist Doctor** | `dr.sharma@hospital.local` | `DoctorPass@2026` | Cardiology OPD Consultations, Inpatient Prescriptions |
| **Admitted Patient** | `patient2@hospital.local` | `PatientPass@2026` | Inpatient Room 301, Discharge & Billing Lifecycle |
| **Outpatient** | `patient1@hospital.local` | `PatientPass@2026` | Outpatient Appointments, Rx & Invoices |
