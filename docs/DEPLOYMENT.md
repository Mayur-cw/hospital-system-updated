# Production Deployment Guide: Hedgewar Hospital Care

This document details the production deployment, environment configuration, first-run initialization, and disaster recovery procedures for **Hedgewar Hospital Care**.

---

## 1. Environment Variable Reference

All configuration values can be provided via environment variables or a `.env` file in the application root directory.

| Variable Name | Type | Default | Required in Prod | Description |
|---|---|---|---|---|
| `FLASK_ENV` | String | `development` | **Yes** | Set to `production` in live environments. Disables debug mode and blocks demo seeding. |
| `SECRET_KEY` | String | *(dev-insecure-key)* | **Yes** | Cryptographically secure random secret (min 32 bytes) used for session signing and CSRF tokens. |
| `DATABASE_URL` | String | `sqlite:///hms_dev.db` | **Yes** | SQLAlchemy connection URI. Production must use MySQL 8.0+ (`mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>`). |
| `RATELIMIT_STORAGE_URI` | String | `memory://` | **Yes** | Redis storage URI for distributed rate limiting (`redis://<host>:6379/0`). |
| `PAYMENT_GATEWAY` | String | `mock` | Recommended | `razorpay` for live gateway processing, or `mock` for staging/dev test transactions. |
| `RAZORPAY_KEY_ID` | String | `""` | If Razorpay | Merchant API Key identifier provided by Razorpay. |
| `RAZORPAY_KEY_SECRET` | String | `""` | If Razorpay | Merchant API Secret Key provided by Razorpay for webhook HMAC validation. |
| `MAIL_SERVER` | String | `localhost` | Recommended | SMTP server hostname or IP (e.g., Mailpit in dev, AWS SES / SendGrid in prod). |
| `MAIL_PORT` | Integer | `1025` | Recommended | SMTP server port (e.g. 1025 for Mailpit, 587 for TLS, 465 for SSL). |
| `MAIL_USE_TLS` | Boolean | `False` | Recommended | Enable STARTTLS for outbound SMTP traffic. |
| `MAIL_USERNAME` | String | `""` | Optional | SMTP authentication username. |
| `MAIL_PASSWORD` | String | `""` | Optional | SMTP authentication password. |
| `MAIL_DEFAULT_SENDER` | String | `no-reply@hedgewar.hospital` | Recommended | Default email address for outbound appointment and invoice notifications. |
| `ALLOWED_HOSTS` | String | `*` | **Yes** | Comma-separated list of permitted HTTP `Host` headers to prevent host header injection. |
| `SESSION_COOKIE_SECURE` | Boolean | `False` | **Yes** | Enforces HTTPS-only transmission of session cookies in production. |
| `WTF_CSRF_TIME_LIMIT` | Integer | `3600` | No | Lifetime of CSRF tokens in seconds (default: 1 hour). |
| `SENTRY_DSN` | String | `""` | Optional | Outbound crash monitoring DSN with automated PHI sanitization hook (`scrub_phi`). |

---

## 2. First-Run Production Checklist

Follow these exact steps when initializing a new production deployment:

### Step 1: Provision Persistent Storage & Database
Ensure MySQL 8.0+ is running with `utf8mb4` character set and `utf8mb4_unicode_ci` collation:
```sql
CREATE DATABASE hms_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'hms_user'@'%' IDENTIFIED BY 'StrongGeneratedPassword#123';
GRANT ALL PRIVILEGES ON hms_prod.* TO 'hms_user'@'%';
FLUSH PRIVILEGES;
```

### Step 2: Apply Database Schema Migrations
Always run Alembic migrations rather than calling `create_all()`. This creates versioned tables, unique generated columns, and foreign key constraints:
```bash
export FLASK_APP=hms
export DATABASE_URL="mysql+pymysql://hms_user:StrongGeneratedPassword%23123@127.0.0.1:3306/hms_prod"
flask db upgrade
```

### Step 3: Provision the Root Administrator Account
Execute the interactive CLI command to provision the root administrator without echoing secrets into shell history:
```bash
flask create-admin --email "admin@hedgewar.hospital" --username "Executive Administrator"
```
You will be prompted to enter a password confirming to the hospital security policy ($\ge 10$ characters, upper, lower, digit, symbol).

### Step 4: Configure Hospital Settings
1. Log in to the application at `/login` as the new administrator.
2. Navigate to **Admin Settings** (`/admin/settings`).
3. Set your hospital's official legal name, 24/7 emergency telephone helpline, physical address, and cancellation grace period.

### Step 5: Verify Container Health Probes
Confirm the application liveness and readiness probes respond with HTTP 200:
```bash
curl -I http://127.0.0.1:5000/healthz   # HTTP/1.1 200 OK
curl -I http://127.0.0.1:5000/readyz     # HTTP/1.1 200 OK
```

---

## 3. Worked Deployment Examples

### Option A: Docker Compose (Standard VM / Bare-Metal)

1. Clone repository to `/opt/hms/app`:
   ```bash
   git clone https://github.com/HedgewarHospital/hospital-management-system.git /opt/hms/app
   cd /opt/hms/app
   ```
2. Copy environment template and fill in production secrets:
   ```bash
   cp .env.example .env
   # Edit .env with your production values
   ```
3. Build and launch services in detached mode:
   ```bash
   docker compose up -d --build
   ```
4. Run migrations and provision admin:
   ```bash
   docker compose exec web flask db upgrade
   docker compose exec web flask create-admin --email "admin@hedgewar.hospital" --username "Admin"
   ```

### Option B: Cloud PaaS (Render, Railway, Fly.io)

1. **Database:** Create a managed MySQL 8 service. Copy the connection string.
2. **Web Service:**
   - Source: Connect GitHub repository.
   - Environment: Python 3.12 (or Dockerfile).
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --config gunicorn.conf.py "hms:create_app()"`
   - Healthcheck Path: `/healthz`
3. **Environment Variables:** Add `DATABASE_URL`, `SECRET_KEY`, `FLASK_ENV=production`, `ALLOWED_HOSTS`.
4. **Post-Deploy:** Run `flask db upgrade` in the PaaS terminal or build script.

---

## 4. Disaster Recovery & Backup Routine

- **Automated Backup:** Schedule `scripts/backup.sh` via crontab every 6 hours:
  ```crontab
  0 */6 * * * /opt/hms/app/scripts/backup.sh >> /var/log/hms_backup.log 2>&1
  ```
- **Disaster Recovery Runbook:** Refer to [backup_and_restore.md](file:///Users/mayur/Sab_Kaam_ka/devlopment/my_projects/1.HMS/Hospital%20management%20system/docs/backup_and_restore.md) for RPO ($< 1\text{h}$) and RTO ($< 30\text{m}$) point-in-time recovery steps.
