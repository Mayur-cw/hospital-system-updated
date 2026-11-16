# EVIDENCE: T-00 EARLY SAFE SERVER LAUNCH
**Date:** 2026-11-17  
**Verification Method:** Live HTTP probe via curl and health check  
**URL:** `http://127.0.0.1:5001/`  
**Health Check:** `http://127.0.0.1:5001/health`  
**Result:** HTTP 200 OK  
**Security Profile:**
- `FLASK_DEBUG`: `false` (default enforced)
- `SECRET_KEY`: securely generated ephemeral secret in dev; fails closed in prod
- `DATABASE_URL`: local SQLite file `instance/hms_dev.db`; no root DB credentials
- `CSRF`: `WTF_CSRF_ENABLED=True`
- `DEMO_ONLY`: `True`
