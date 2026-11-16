# HOSPITAL OS — OPERATIONS & RUNBOOK
**System:** Hospital Information System / Hospital OS  
**Architecture:** Evolutionary Modular Monolith (Python 3.9+ / Flask / SQLAlchemy)  
**Target Environment:** Local Development / On-Premises Linux Server / Cloud Container  
**Date:** November 2026

---

## 1. Service Architecture & Process Lifecycle

### 1.1 Process Management
- **Application Factory:** `PROJECT/app.py:create_app()`
- **WSGI Entry Point:** Run via Gunicorn or uWSGI for production; Flask CLI for local development.
- **Port:** Local development defaults to `PORT=5001` (to prevent conflict with macOS AirPlay on port 5000).

### 1.2 Local Development Startup
```bash
# 1. Activate isolated Python environment
source .venv/bin/activate

# 2. Set environment variables
export APP_ENV=development
export PORT=5001
export FLASK_DEBUG=0
export SECRET_KEY=local-dev-synthetic-secret-key-32-chars-min!

# 3. Seed synthetic database (if starting fresh)
python scripts/seed_synthetic.py

# 4. Start local development server
python PROJECT/app.py
```

### 1.3 Production Deployment Standard
```bash
# Production command (via gunicorn with 4 worker processes)
gunicorn --workers 4 \
         --bind 0.0.0.0:8000 \
         --access-logfile - \
         --error-logfile - \
         "PROJECT.app:create_app()"
```

> [!IMPORTANT]
> In `APP_ENV=production`, `Config.validate()` fails closed immediately if `SECRET_KEY` is not provided or if `DATABASE_URL` is missing. The server will refuse to start to protect patient data security.

---

## 2. Health Probes & Monitoring

### 2.1 Health Check Endpoint
- **URL:** `GET /health`
- **Response Format:** JSON
- **Success (HTTP 200):**
  ```json
  {
    "status": "UP",
    "database": "healthy",
    "mode": "DEMO_ONLY",
    "environment": "development",
    "timestamp": "2026-11-16T19:30:10.904984"
  }
  ```
- **Degraded / Error (HTTP 503):**
  ```json
  {
    "status": "DEGRADED",
    "database": "unhealthy",
    "error": "Connection refused",
    "timestamp": "..."
  }
  ```

### 2.2 Alerting Thresholds
- Database probe failure: Page on-call systems administrator immediately.
- 5xx error rate > 1% over 5-minute rolling window: High priority alert.
- Process memory > 1.5 GB per worker: Worker recycling alert.

---

## 3. Database Backup & Recovery Procedures

### 3.1 Local SQLite Backup
```bash
# Create point-in-time snapshot
sqlite3 instance/hms_dev.db ".backup 'backups/hms_dev_$(date +%Y%m%d_%H%M%S).db'"
```

### 3.2 Production MySQL / PostgreSQL Backup
```bash
# Automated daily logical dump
mysqldump --single-transaction \
          --quick \
          --routines \
          --triggers \
          --user=$DB_USER \
          --password=$DB_PASS \
          hms_prod | gzip > /var/backups/hms_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 3.3 Recovery & Restore Verification
1. Halt active application traffic or direct traffic to a maintenance page.
2. Restore database into a staging environment or clean target database.
3. Run automated integrity test suite:
   ```bash
   pytest tests/test_billing_integrity.py tests/test_clinical_safety.py
   ```
4. Verify record checksums and non-destructive amendment logs.
5. Reroute production traffic back to restored cluster.

---

## 4. Role Accounts & Synthetic Testing Matrix

| Role | Username / Email | Password | Primary Workflow |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@hospital.local` | `Admin@Hospital123!` | System configuration, room setup, user management, audit logs |
| **Receptionist** | `receptionist@hospital.local` | `Reception@Hospital123!` | Patient registration, de-dup check, OPD check-in & token generation |
| **Doctor** | `dr.sharma@hospital.local` | `Doctor@Hospital123!` | OPD consultation workspace, clinical notes, signing, prescription |
| **Doctor** | `dr.patel@hospital.local` | `Doctor@Hospital123!` | Orthopedic consultation and inpatient rounds |
| **Cashier** | `cashier@hospital.local` | `Cashier@Hospital123!` | Invoice settlement, drawer reconciliation, official receipt issue |
| **Patient** | `patient1@hospital.local` | `Patient@Hospital123!` | Self-service portal, view upcoming appointments, view receipts |

---

## 5. Security Incident Response
1. **Compromised Session / Token:**
   - Execute `/logout` across active sessions.
   - Rotate `SECRET_KEY` in environment variables and restart Gunicorn workers.
2. **Clinical Note Dispute:**
   - Review `ClinicalNoteRevision` table for full forensic timestamp, author ID, and historical note body.
   - Clinical notes cannot be modified in-place; all revisions are append-only.
