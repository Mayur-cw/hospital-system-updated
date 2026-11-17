# Hospital OS — Modern Clinical & Hospital Information System

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.x](https://img.shields.io/badge/flask-3.1.3-green.svg)](https://palletsprojects.com/p/flask/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security: pip-audit clean](https://img.shields.io/badge/security-pip--audit%20clean-brightgreen.svg)](requirements.txt)

Hospital OS is a role-aware Hospital Management System engineered with clinical safety, data integrity, and strict access control. Built with Python 3.12, Flask 3, and SQLAlchemy 2.

---

## Quickstart

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/Mayur-cw/hospital-system-updated.git
cd hospital-system-updated
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Initialize Demo Data
```bash
flask --app PROJECT/app.py seed-demo
```
*(Randomized credentials will be generated and printed once in your terminal).*

### 4. Run Development Server
```bash
flask --app PROJECT/app.py run --port 5000
```

### 5. Run Test Suite
```bash
pytest -v
```

---

## System Architecture

```mermaid
graph TD
    Client[Web Browser / Client] --> Routes[Flask Blueprints]
    Routes --> Policies[Central RBAC & Object Policies]
    Policies --> Services[Domain Services: Billing, Appointments, Inpatient, Records]
    Services --> Models[SQLAlchemy 2.x ORM Models]
    Models --> DB[(MySQL 8 / SQLite Engine)]
    Services --> AuditLog[(Append-Only Audit Trail)]
```

---

## Roadmap & Tracking

Every planned upgrade, architectural decision, and bug remediation is tracked under [`CHANGES.md`](CHANGES.md).
