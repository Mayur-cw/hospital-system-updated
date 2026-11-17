# Phase 2 — Security Hardening & Authorization Architecture

**Date:** November 17, 2026  
**Status:** Completed  
**Branch:** `phase-2-security`  
**Gate Status:** Green (`pytest` 46 passed across SQLite & native MySQL 9.6, `pip-audit` zero vulnerabilities, `ruff` clean)

---

## 1. What Changed (with Change IDs)

* **S-01 (CSRF Protection Everywhere):** Integrated Flask-WTF `CSRFProtect` globally. Injected `{{ csrf_field() }}` across all 34 POST forms and added `X-CSRFToken` request headers to client-side AJAX `fetch()` calls. Form POSTs without valid tokens return HTTP 400 Bad Request.
* **S-02 (Logout via POST):** Converted `/logout` from an unsafe GET link to a secure POST form with CSRF token, preventing involuntary logout via malicious image tags or CSRF probes. GET requests to `/logout` return HTTP 405 Method Not Allowed.
* **S-03 (Open Redirect Prevention):** Created `safe_redirect` and `is_safe_url` in `hms/utils/security.py`. Strictly rejects external domains, protocol-relative paths (`//evil.com`), backslash bypasses (`\\\\evil.com`), and javascript schemes.
* **S-04 (Rate Limiting & Abuse Prevention):** Integrated `Flask-Limiter` with client IP keying across high-risk endpoints (`/login`, `/signup`, `/forgot-password`). Excessive requests trigger HTTP 429 Too Many Requests with user-friendly retry notices.
* **S-05 (Central RBAC & Object-Level Authorization):** Implemented `@roles_required`, `@admin_bp.before_request`, and object-level policy functions (`can_view_appointment`, `can_modify_appointment`, `can_view_invoice`, `can_edit_medical_record`, `can_view_medical_record`, `can_manage_admissions`). Replaced hardcoded string matching with `abort(403)` on unauthorized cross-role or cross-user operations.
* **S-06 (Password Policy):** Enforced modern password policy: minimum 10 characters, automatic rejection of known breached/common passphrases (e.g. `password123`, `admin12345`), and strict preservation of leading/trailing whitespace (never silently `.strip()`).
* **S-07 (Session & Cookie Hardening):** Enabled `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, and `session_protection = 'strong'`. Enforces 2-hour idle session lifetime.
* **S-08 (Security Headers & Anti-Caching):** Configured `Flask-Talisman` for `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, and `Referrer-Policy: strict-origin-when-cross-origin`. Applied `Cache-Control: no-store, no-cache, must-revalidate` to all clinical, prescription, and billing endpoints.
* **S-09 (Fail-Closed Error Handlers & Request Tracing):** Disabled `FLASK_DEBUG` by default. Implemented custom branded error templates (`400.html`, `403.html`, `404.html`, `429.html`, `500.html`) and structured JSON error responses with unique correlation request IDs (`X-Request-ID`), concealing all internal tracebacks and database schemas.
* **S-12 (Account Lifecycle & Signed Reset Tokens):** Implemented password reset using `itsdangerous.URLSafeTimedSerializer` with cryptographically signed, tamper-resistant tokens expiring within 30 minutes.

---

## 2. Design Trade-offs & Decisions

### Choice 1: HTTP 403 Forbidden vs Silent Home Page Redirects
* **Alternative A (Legacy):** When a patient attempted to access an admin page or another patient's invoice, the app flashed "Unauthorized" and redirected to `/`.
  * *Downside:* Obscured authorization violations, broke RESTful conventions, and complicated automated security scanners.
* **Alternative B (Chosen — S-05):** Return standard HTTP 403 Forbidden with incident correlation identifier `X-Request-ID`.
  * *Why chosen:* Enforces clear security boundaries, satisfies authorization matrix requirements (T-04), and provides transparent auditing for intrusion detection.

### Choice 2: Signed Expiring Tokens vs Database Reset Tokens
* **Alternative A (Considered):** Storing plain random tokens in a `password_resets` table.
  * *Downside:* Requires database writes, cleanup jobs for expired tokens, and table bloat.
* **Alternative B (Chosen — S-12):** `itsdangerous.URLSafeTimedSerializer` with application `SECRET_KEY`.
  * *Why chosen:* Stateless, tamper-proof, automatically cryptographically enforces time boundaries (30 minutes), and requires zero storage overhead.

---

## 3. Automated Test Verification

All security mechanisms are verified by automated tests in `tests/unit/test_phase2_security.py`:
- `test_s01_csrf_protection_rejects_missing_token` (PASSED)
- `test_s02_logout_requires_post` (PASSED)
- `test_s03_open_redirect_prevention` (PASSED)
- `test_s04_rate_limiting_triggers_429` (PASSED)
- `test_s05_rbac_authorization_matrix` (PASSED)
- `test_s06_password_strength_policy` (PASSED)
- `test_s06_signup_enforces_password_policy` (PASSED)
- `test_s07_s08_security_headers_and_cache_control` (PASSED)
- `test_s09_custom_error_pages` (PASSED)
- `test_s12_expiring_signed_reset_tokens` (PASSED)
- `test_s12_password_reset_flow` (PASSED)
- Total test suite: 46 passing tests (0 failures, 0 xfails).
