# Contributing to Hospital OS

Thank you for contributing to Hospital OS.

## Development Workflow

1. **Python Environment:** Use Python 3.12 (`python3.12 -m venv .venv`).
2. **Dependencies:** Install dependencies from `requirements.txt` and `requirements-dev.txt`.
3. **Commit Conventions:** Follow conventional commits referencing `CHANGES.md` IDs:
   - `fix(B-01): ...`
   - `feat(F-01): ...`
   - `chore(H-01): ...`
4. **Testing Gate:** All pull requests must pass the test suite:
   ```bash
   pytest -v
   pip-audit -r requirements.txt
   ruff check .
   black --check .
   ```
5. **Security & Clinical Safety:**
   - Never commit plaintext credentials or fallback secrets.
   - Enforce fail-closed configuration in production.
   - Never use `float` for monetary balances.
   - Never execute hard deletes on medical or financial records.
