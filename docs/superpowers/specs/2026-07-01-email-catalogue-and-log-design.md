# Email Catalogue + Email Log — Design

**Date:** 2026-07-01
**Status:** Approved (pending spec review)
**Context:** Follows the notifications sprint (N-1/N-2/N-3). SPT wants to (a) review the
canonical wording of every email the platform sends, and (b) see a live record of the
emails that were actually sent, all from Django `/admin`.

## Goals

1. **Email catalogue** — a read-only, browsable reference in `/admin` listing every email
   type the system can send, with its trigger, recipients, subject and body (placeholders
   shown for dynamic parts). Source of truth is code, so it cannot silently drift.
2. **Email log** — a live audit trail in `/admin` of every email actually sent (recipient,
   subject, full body, status), captured automatically for all send paths.

Non-goals: editing email wording from admin (catalogue is read-only); changing any existing
email's content or delivery behaviour.

## The 8 email types

| key | name | trigger | subject | fixed/dynamic |
|-----|------|---------|---------|---------------|
| `message` | New message | someone messages the recipient | `New message from {sender}` | dynamic |
| `scholar_forum_post` | Scholar forum post | matched scholar posts in a visible forum | `{scholar} posted in the forum` | dynamic |
| `notification_digest` | Notification digest | debounce window closes with ≥2 unread pending | `You have {n} new notifications on SPT Mentoring` | dynamic |
| `mass_message` | Mass message | admin broadcast | admin-authored per send | dynamic |
| `no_contact_reminder` | No-contact reminder | Beat: pair silent ≥ NO_CONTACT_REMINDER_DAYS | `SPT Mentoring – Time to connect!` | fixed |
| `sponsor_update_reminder` | Sponsor update reminder | Beat: scholar overdue to sponsor | `SPT Scholarships – Time to update your sponsor` | fixed |
| `moderation_alert` | Moderation alert | message/post flagged for review | `[SPT Moderation] Flagged message requires review (#{id})` | fixed |
| `password_reset` | Password reset | user requests a reset | `Reset your password — Arkwright Mentoring` | fixed |

Single message/forum emails (keys `message`, `scholar_forum_post`) are debounced by N-3 and,
when ≥2 are pending, are delivered as a single `notification_digest` instead.

## Feature 1 — Email catalogue

### Registry (single source of truth)
`apps/notifications/email_catalogue.py` defines `EMAIL_CATALOGUE`: a list of `EmailSpec`
dataclass entries, one per email type:

```python
@dataclass(frozen=True)
class EmailSpec:
    key: str            # stable identifier, e.g. "password_reset"
    name: str           # human label
    trigger: str        # when it is sent
    recipients: str     # who receives it
    subject: str        # literal for fixed emails; "{placeholder}" pattern for dynamic
    body: str           # ditto
    debounced: bool     # subject to N-3 debounce
    source: str         # module path where it is actually sent, for cross-reference
    notes: str = ""
```

### Anti-drift
For the four **fixed** emails, the exact subject/body strings are extracted into module-level
constants (or small `build_*` helpers) in the modules that already send them, and both the
real sender and the catalogue import the same constant:

- `apps/messaging/tasks.py` — `NO_CONTACT_REMINDER_SUBJECT` + `build_no_contact_body(first_name)`,
  `SPONSOR_UPDATE_SUBJECT` + `build_sponsor_update_body(...)`.
- `apps/moderation/service.py` — `build_moderation_alert(message, term, url)` → (subject, body).
- `apps/users/auth_views.py` — `PASSWORD_RESET_SUBJECT` + `build_password_reset_body(first_name, url)`.

The sender is refactored to call these; the catalogue renders them with sample values. This
guarantees the catalogue matches what is actually sent. Dynamic emails (`message`,
`scholar_forum_post`, `notification_digest`, `mass_message`) reference the existing builders
(`notifications.emails`, `notifications.digest`) or document the placeholder pattern.

A test asserts every `EmailSpec.key` is unique and that the fixed-email constants used by the
senders are the same objects referenced by the catalogue (no divergence).

### Model
`EmailCatalogueEntry` (managed) — a display projection of the registry:
`key` (unique), `name`, `trigger`, `recipients`, `subject`, `body`, `debounced`, `source`,
`notes`, `updated_at`. It holds no authoritative data; it is rebuilt from the registry.

### Sync command
`python manage.py sync_email_catalogue` — idempotent: upserts one row per `EmailSpec` (keyed
by `key`) and deletes rows whose key is no longer in the registry. Run on deploy.

### Admin
`EmailCatalogueEntryAdmin` — read-only: `has_add_permission` and `has_delete_permission`
return False, all fields read-only. List shows name/trigger/recipients/debounced; detail
shows subject + body. Add to the Jazzmin icon map (per the admin-registration gotcha).

## Feature 2 — Email log

### Capture point: a wrapping email backend
`config/logging_email_backend.py` → `LoggingEmailBackend(BaseEmailBackend)`:

- On init, instantiate the real backend named by `settings.LOGGED_EMAIL_BACKEND`.
- `send_messages(messages)`: for each `EmailMessage`, write an `EmailLog` row, then delegate
  the whole batch to the real backend; record per-message status (sent/failed) and any error.
- **Fail-safe:** all logging is wrapped in try/except and logged to the app logger; a logging
  failure never prevents or breaks the actual send. Conversely a send failure is recorded on
  the log row (`status='failed'`, `error=...`).

Settings:
```python
EMAIL_BACKEND = 'config.logging_email_backend.LoggingEmailBackend'
LOGGED_EMAIL_BACKEND = config('LOGGED_EMAIL_BACKEND',
                              default='config.smtp2go_backend.SMTP2GOEmailBackend')
```
(In dev/tests the wrapped backend is console/locmem; Django still overrides `EMAIL_BACKEND`
to locmem inside its own test runner, so the backend is unit-tested explicitly.)

### Model
`EmailLog`: `to` (comma-joined recipients), `from_email`, `subject`, `body` (TextField, full),
`status` (`sent` | `failed`), `error` (blank), `category` (best-effort key, blank if unknown),
`created_at` (indexed). Category is inferred by matching the subject against known catalogue
subjects/prefixes; unknown → blank. Full bodies are stored, including reset links (accepted:
admins are trusted; tokens are single-use/short-lived).

### Admin
`EmailLogAdmin` — read-only fields, no add/edit; **delete allowed** for manual cleanup. List:
created_at, to, subject, category, status. Filters: status, category, created_at. Search:
to, subject. Add to the Jazzmin icon map.

### Auto-prune
Celery Beat task `purge_email_logs_task` (in `apps/notifications/tasks.py`) deletes
`EmailLog` rows older than `settings.EMAIL_LOG_RETENTION_DAYS` (default 90, env-overridable).
Scheduled daily in `config/celery.py` (e.g. 03:15).

## Testing

- **Catalogue:** `sync_email_catalogue` creates the expected rows; re-running is idempotent;
  removing a registry entry deletes its row; admin is read-only; fixed-email constants are the
  same objects used by senders (anti-drift).
- **Log:** `LoggingEmailBackend` writes one `EmailLog` per message and delegates to the inner
  backend (assert inner received them / locmem outbox); a send failure is recorded as
  `failed`; a DB/logging error does not prevent the send; category inference matches known
  subjects; `purge_email_logs_task` deletes only rows older than the cutoff.
- Existing 181 tests stay green (refactors of fixed-email senders must not change output —
  pinned by asserting sent subject/body equal the extracted constants).

## Migrations
One migration adding `EmailCatalogueEntry` and `EmailLog` (notifications app).

## Deployment
1. Apply migrations.
2. `python manage.py sync_email_catalogue`.
3. Set `EMAIL_BACKEND` to the logging backend (and `LOGGED_EMAIL_BACKEND` to SMTP2GO) in the
   prod `.env`.
4. Restart backend, worker, beat (new backend, new task, new schedule). Add the two models to
   the Jazzmin icon map.

## Security / privacy notes
- Email bodies (incl. password-reset links and message text) are stored in `EmailLog` in full
  and visible to any admin. Accepted by SPT. Retention limits exposure window via auto-prune.

## Out of scope
- Editing email wording from admin (would require templating every send path).
- Resend / retry from admin.
- HTML-body rendering/preview (system sends plain-text emails).
