# EVIDENCE: PHASE T-00 RUNTIME BASELINE & TEST SUITE INVENTORY
**Date:** 2026-11-17  
**Auditor:** Antigravity  
**Commit:** `ec332d26d815434e817b1b49e66c83311f5dc79d`

---

## 1. Initial Test Suite Audit
- **Tests present in original repository:** **0 tests**
- **Test frameworks configured in original repository:** None
- **CI/CD workflows present:** None

---

## 2. Characterization Testing Baseline
Before refactoring the codebase, we established a clean virtual environment (`.venv`) with Python 3.9.6, installed core and test dependencies (`pytest`, `pytest-cov`, `Flask-WTF`, `alembic`, `python-dotenv`), and created initial characterization test suites to establish empirical baseline behavior.

### Baseline Vulnerability Verification:
1. **Config & Environment**: Verified `FLASK_DEBUG` evaluates to `'true'` by default when unset. Verified `Config.SQLALCHEMY_DATABASE_URI` points to `mysql://root:Mayur@localhost/hms` by default.
2. **Open Redirect**: Verified `auth.login` accepts arbitrary external URLs in `request.args.get('next')`.
3. **GET Logout**: Verified `auth.logout` accepts `GET` requests and mutates session state.
4. **BOLA / IDOR in Doctor actions**:
   - `doctor.mark_missed(apt_id)` only checks `current_user.usertype != "Doctor"`. Does not check `doctor.username == appointment.doctor` or `doctor.did`.
   - `doctor.mark_attended(apt_id)` only checks `current_user.usertype != "Doctor"`.
   - `doctor.add_record(apt_id)` only checks `current_user.usertype != "Doctor"`.
   - `doctor.discharge_patient()` checks neither admission assignment nor whether admission is already discharged.
5. **False Payment**: Verified `patient.process_payment` sets `invoice.status = 'Paid'` on POST with zero verification.

All 5 core vulnerability classes confirmed via source code analysis and characterization test harness.
