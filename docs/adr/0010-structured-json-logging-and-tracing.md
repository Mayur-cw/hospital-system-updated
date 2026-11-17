# ADR 0010: Structured Single-Line JSON Logging & PHI Redaction (D-10)

## Status
Accepted

## Context
Standard text logs lack correlation identifiers across microservices or reverse proxies and risk inadvertently dumping protected health information (PHI) such as patient names, clinical symptoms, and medical notes into cloud log aggregators.

## Decision
We engineered `hms/logging.py`:
- `JSONFormatter`: Formats every log event into a single-line JSON string containing `timestamp`, `request_id`, `user_id` (numeric ID only), `method`, `path`, `status`, and `latency_ms`.
- `X-Request-ID`: Extracted from incoming proxy headers or generated as a UUID v4, propagated in responses and user error pages.
- `scrub_phi`: Recursive data sanitizer that redacts credentials, passwords, session tokens, medical diagnoses, and clinical notes before output.

## Consequences
- Structured log streams easily ingested by CloudWatch, Datadog, ELK, or Grafana Loki.
- Strict compliance with health privacy standards: zero unredacted PHI in logs.
