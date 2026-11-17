# ADR 0008: Transactional Outbox Pattern for Notifications (D-08)

## Status
Accepted

## Context
Dispatching notifications (emails, SMS, WhatsApp) synchronously during HTTP requests risks hanging user web requests if the external mail server or gateway is slow or unreachable. Rolling back a database transaction after an external HTTP call has already succeeded leaves duplicate or ghost notifications.

## Decision
We adopted the Transactional Outbox Pattern:
- `NotificationOutbox`: Notifications are written into a database table (`notification_outbox`) within the exact same database transaction as the business event (booking, rescheduling, cancellation, invoice).
- `InAppNotification`: In-app notification cards are also created within the transaction.
- Outbound delivery is decoupled and dispatched by asynchronous background workers or CLI tasks (`flask send-reminders`).

## Consequences
- Atomicity: If the transaction rolls back, no false notification is queued.
- Resilient retry: Failed notification dispatches can be retried without impacting client request latency.
