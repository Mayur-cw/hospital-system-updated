# Phase 0 Notes — Hygiene and Safety Net

**Date:** 2026-11-17  
**Branch:** `phase-0-hygiene`  
**Status:** Completed  

---

## 1. What Changed

* **H-01 (Repo Hygiene):** Removed 2,433 committed virtualenv files (`venv/`, `PROJECT/venv/`), `.vscode/`, and OS metadata files (`.DS_Store`) from git index. Added a production-grade [`.gitignore`](../../.gitignore). Tracked file count dropped from 2,479 to 42.
* **H-02 (Secrets & Config):** Replaced hard-coded fallback secrets and root MySQL credentials in [`PROJECT/config.py`](../../PROJECT/config.py) with environment-aware classes (`DevelopmentConfig`, `TestingConfig`, `ProductionConfig`). Enforced fail-closed behavior in production: booting in production without a secure `SECRET_KEY` or valid `DATABASE_URL` immediately halts with a descriptive `RuntimeError`. Added [`.env.example`](../../.env.example).
* **H-03 (Credential Sanitization & CLI):** Purged plaintext seed passwords from [`seed_secure_accounts.sql`](../../seed_secure_accounts.sql). Built [`PROJECT/cli.py`](../../PROJECT/cli.py) with `flask create-admin` (interactive secure password prompt) and `flask seed-demo` (generates random passwords printed once, refuses to run when `APP_ENV=production`).
* **H-04 (Modern Dependencies):** Upgraded baseline to Python 3.12, Flask 3.1.3, Werkzeug 3.1.9, and SQLAlchemy 2.x. Created root [`requirements.txt`](../../requirements.txt) and [`requirements-dev.txt`](../../requirements-dev.txt). Added [`.github/dependabot.yml`](../../.github/dependabot.yml). Verified zero known vulnerabilities using `pip-audit`.
* **H-05 (Dead Code Elimination):** Removed obsolete `Test` model in [`PROJECT/models.py`](../../PROJECT/models.py), deleted `testing.sql`, unreferenced `PROJECT/static/css/virtualregister.css`, and `Commands/one step command.txt`.
* **H-06 (Safety Net & Characterization):** Created automated pytest suite in [`tests/unit/test_smoke_characterization.py`](../../tests/unit/test_smoke_characterization.py). Verified working baseline flows (signup, login, doctor queue, clinical notes) and pinned known Phase 1 defects (`B-01`, `B-03`, `B-04`, `B-06`, `B-08`, `B-10`, `B-24`) with `xfail(strict=True)`.
* **H-07 (Documentation):** Added [`README.md`](../../README.md), [`LICENSE`](../../LICENSE), [`CONTRIBUTING.md`](../../CONTRIBUTING.md), and this phase report.

---

## 2. Why This Approach (Design Review Trade-offs)

### Virtualenv Storage: Git Tracking vs Rebuilding
* **Alternative 1 (Keep committed venv):** "Quick to run on that specific machine." *Rejected:* Binaries compiled on macOS do not run on Linux servers; bloating git history by 32+ MB slows down every clone and merge.
* **Chosen:** Git tracks only code and exact dependency specifications (`requirements.txt`). Virtual environments are ephemeral and built on-demand.

### Secret Management: Fallback Defaults vs Fail-Closed
* **Alternative 1 (Convenient dev fallbacks in production):** App boots with default `SECRET_KEY='hmsprojects_dev_key'` if missing. *Rejected:* In production, anyone knowing the default secret can forge signed session cookies and hijack administrator accounts.
* **Chosen:** Fail-closed. In production, if required secrets are absent, the application refuses to boot, protecting patient data before a single request is served.

### Testing Baseline: Refactor Immediately vs Characterization Tests First
* **Alternative 1 (Fix bugs directly):** Start editing code immediately. *Rejected:* Without tests proving what currently works and what currently fails, fixes can silently break working flows without anyone noticing.
* **Chosen:** Characterization tests pin current behavior first. Bugs are marked with `@pytest.mark.xfail(strict=True)`. When a bug is fixed, the test flips from xfail to pass.

---

## 3. Concepts to Understand

1. **Why Untracking Virtualenvs Matters:**  
   Virtual environments contain compiled C-extensions (like `.so` files) and platform-specific binaries. Committing them creates repository bloat, merge conflicts, and immediate breakage when deployed to different operating systems (e.g. Linux Docker containers).
2. **Fail-Closed Security Design:**  
   "Fail-closed" means that in the absence of valid credentials or security configurations, a system defaults to rejecting access or refusing to start, rather than falling back to an insecure default.
3. **Characterization Testing with Strict XFail:**  
   Characterization tests document how the software currently behaves (both its features and its bugs). Tagging known defects with `@pytest.mark.xfail(strict=True)` ensures that if a defect is accidentally triggered or resolved, pytest notifies you immediately.

---

## 4. Try It Yourself

Execute these commands in your terminal to observe Phase 0 in action:

1. **Inspect Tracked File Hygiene:**
   ```bash
   git ls-files | wc -l
   # Output will be ~45-50 files (down from 2,479)
   ```

2. **Verify Fail-Closed Production Startup:**
   ```bash
   APP_ENV=production python -c "import sys; sys.path.insert(0, 'PROJECT'); from config import get_config; get_config('production')"
   # Observe the immediate RuntimeError refusing startup without a SECRET_KEY
   ```

3. **Run the Characterization Test Suite:**
   ```bash
   pytest -v tests/unit/test_smoke_characterization.py
   # Observe: 4 passed, 8 xfailed, 0 errors
   ```

4. **Verify Dependency Security Audit:**
   ```bash
   pip-audit -r requirements.txt
   # Output: "No known vulnerabilities found"
   ```

---

## 5. Self-Check (Review Questions)

1. *Why should `.env` never be committed to git, while `.env.example` must be committed?*
2. *What happens in `PROJECT/config.py` if someone tries to deploy with a hardcoded root MySQL password in `DATABASE_URL`?*
3. *Why do we use `strict=True` on `@pytest.mark.xfail` instead of just ignoring the test?*
4. *How does `flask seed-demo` protect production environments from being overwritten with demo data?*
5. *Why is `git ls-files` a better indicator of tracked repository state than `ls`?*
