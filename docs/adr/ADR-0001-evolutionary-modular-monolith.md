# ADR-0001: Evolutionary Modular Monolith Architecture
**Date:** 2026-11-17  
**Status:** ACCEPTED  
**Deciders:** Staff Engineer, Product Owner, DevOps/SRE

## Context
The existing repository `hospital-system-updated` is implemented with Python, Flask, Flask-SQLAlchemy, Flask-Login, and Jinja2 templates. While functional at a basic level, the codebase has unstructured configuration, absence of an application factory, no modular service layer, no CSRF validation, and tight coupling to MySQL-specific stored procedures. 

A greenfield rewrite (e.g. rewriting in Next.js + FastAPI or microservices) was considered. However:
1. Hard constraint #2 mandates: "Target initially small to midsize Indian hospital/OPD, expandable to IPD. Preserve the repository and existing useful Flask/MySQL code wherever safe. No unnecessary rewrite of frontend/backend; write ADR if choosing migration."
2. A rewrite would discard existing working workflows (dashboards, room management, templates) and introduce extensive untested surface area without solving the fundamental clinical safety and data integrity issues.

## Decision
We choose an **Evolutionary Modular Monolith** architecture:
1. Retain Flask, SQLAlchemy, Jinja2, and Bootstrap 5 as the core technology stack.
2. Refactor the application into an **Application Factory pattern** (`create_app(config_name=None)`).
3. Introduce modular boundaries:
   - `core`: Security, central authorization policy, CSRF, audit logging, safe navigation.
   - `identity`: User accounts, staff profiles, patient identity & MRN generation, care relationships.
   - `opd`: Patient registration, provider schedules, appointment state machine, token queue.
   - `clinical`: Encounters, vitals, allergies, structured prescriptions, signed & amended notes.
   - `ipd`: Wards, rooms, beds, admission lifecycle, bed transfer, atomic occupancy, discharge.
   - `billing`: Itemized tariffs, invoices, payment recording (cash / verified webhook), reconciliation.
4. Establish clean layered flow:
   `HTTP Controller (Blueprint Route) -> Schema / Form Validation -> Central Policy Engine -> Domain Service -> SQLAlchemy ORM / DB Constraints -> Audited Events`

## Consequences
- **Positive**:
  - Preserves proven Flask/SQLAlchemy patterns while introducing enterprise-grade safety.
  - Testable in isolation using unit and integration tests with in-memory or SQLite database for rapid CI, while supporting MySQL and PostgreSQL for staging/production.
  - Zero disruption to existing URL contracts while fixing underlying vulnerabilities.
- **Negative / Tradeoffs**:
  - Requires disciplined refactoring of existing routes rather than discarding them.
  - Dual compatibility must be maintained during migration phases.
