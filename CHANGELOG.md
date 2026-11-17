# Changelog

All notable changes to the **Hedgewar Hospital Care** Hospital Management System are documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-17

### Added
- **Phase 0 — Hygiene & Tooling:** Modernized project layout with `pyproject.toml`, Ruff linter, and Pip-Audit security scanner.
- **Phase 3 — Architecture & Data Model:**
  - Migrated to SQLAlchemy 2.0 and modular `hms/` architecture.
  - Unified `DATETIME` (`starts_at`) appointment timestamps and canonical status enums.
  - Added stored generated column `active_slot_key` with unique index enforcing double-booking prevention in MySQL.
  - Strict `Decimal` handling for all financial transactions, invoices, and payments.
  - Soft delete support (`SoftDeleteMixin`) with `ON DELETE RESTRICT` constraints on all clinical and financial records.
- **Phase 1 — Bug Fixes:**
  - Resolved 25 legacy bugs (B-01 through B-25), eliminating crashes in staff creation, slot calculation, date comparisons, and template renderings.
- **Phase 2 — Security Hardening:**
  - Implemented CSRF protection (`Flask-WTF`), HTTP POST logout, open redirect prevention, and centralized RBAC (`hms/policies.py`).
  - Added rate limiting (`Flask-Limiter`), secure session cookies, signed password reset tokens (`itsdangerous`), and MIME validation for file uploads.
- **Phase 4 — Design System & Accessible UI/UX:**
  - Complete CSS variable design system (`tokens.css`, `base.css`, `components.css`) with Light/Dark theme switching.
  - Self-hosted Inter and Outfit webfonts.
  - 100% WCAG 2.2 AA color contrast compliance across 24 semantic token pairs.
  - Eliminated all inline styles (`style=`), `<style>` blocks, and inline `onclick=` handlers.
- **Phase 5 — Core Features:**
  - Reschedule with configurable cutoff window (F-01).
  - RBAC-scoped global typeahead search (F-02).
  - High-performance doctor availability slots API (F-03).
  - State machine with audit logging (F-04).
  - Outbox notification queue for email and in-app alerts (F-05).
  - Payment gateway interface supporting Mock and Razorpay (F-06).
  - Versioned clinical medical records and digital prescription items (F-07).
  - Inpatient bed board, room transfer, and maintenance management (F-08).
  - Administrative system settings and CSV reporting exports (F-09).
  - Dedicated Receptionist role with patient check-in powers (F-10).
  - OpenAPI v1 schema documentation at `/api/v1/openapi.json` (F-11).
  - Server-side cursor/offset pagination helper (F-12).
- **Phase 6 — Reliability & Observability:**
  - Structured single-line JSON logging with request correlation IDs and PHI scrubber (R-01).
  - Microservice-ready `/healthz` and `/readyz` health probes (R-02).
  - Global error handlers for 400, 403, 404, 409, 429, 500, with automatic rollback teardown (R-03).
  - Idempotent CLI scheduler tasks (`flask mark-missed`, `flask send-reminders`) (R-04).
  - Automated transactional backup and restore scripts with SHA-256 integrity checks (R-05).
  - High-throughput Gunicorn WSGI configuration and static cache optimizations (R-06).
- **Phase 7 — Testing & CI/CD:**
  - 110 automated tests covering unit, integration, and E2E patient journeys.
  - Comprehensive `factory_boy` fixtures (`tests/factories.py`).
  - Native MySQL concurrency suite verifying double-booking prevention, idempotent discharge, and duplicate payment webhooks.
  - Automated authorization matrix test derived from Flask's URL map.
  - Broken link crawler and query performance budget checking ($\le 10$ queries per request).
  - GitHub Actions CI workflow (`.github/workflows/ci.yml`) and pre-commit configuration.
  - High test coverage: $\ge 86\%$ across all services and 95% on `hms/policies.py`.
- **Phase 8 — Packaging, Deployment & Documentation:**
  - Multi-stage non-root Dockerfile and Docker Compose environment (App, MySQL 8, Mailpit, Redis).
  - Makefile providing shortcuts for container lifecycle, testing, linting, and seeding.
  - Faker-based `flask seed-demo` generating ~6 months of realistic historical data.
  - Complete documentation suite (`ARCHITECTURE.md`, `DEPLOYMENT.md`, `SECURITY.md`, `billing.md`, `analytics.md`, ADRs 0001–0011).
