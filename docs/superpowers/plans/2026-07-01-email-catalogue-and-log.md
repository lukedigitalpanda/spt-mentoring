# Email Catalogue + Email Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only email *catalogue* (canonical wording of every email type) and a live email *log* (audit of every email actually sent) to Django `/admin`.

**Architecture:** The catalogue is a code registry (`email_catalogue.py`) projected into a read-only `EmailCatalogueEntry` model via a sync command. The log is captured by a `LoggingEmailBackend` that wraps the configured real backend and records every `EmailMessage` into an `EmailLog` model before delegating the send. Fixed-email wording is extracted into shared constants so the catalogue cannot drift from what is actually sent.

**Tech Stack:** Django 4.x, Django admin (Jazzmin), Celery + Celery Beat (Redis), SMTP2GO backend in prod. Tests run via `docker exec spt-mentoring-backend-1 python manage.py test <path> --verbosity=2`.

## Global Constraints

- All new code lives in `apps/notifications/` except the email backend (`config/logging_email_backend.py`) and settings/celery wiring (`config/`).
- Run tests with: `docker exec spt-mentoring-backend-1 python manage.py test <dotted.path> --verbosity=2`.
- Fixed-email refactors MUST NOT change the bytes of any email currently sent — pin with tests asserting the sent subject/body equal the extracted constants.
- Django overrides `EMAIL_BACKEND` to locmem inside its own test runner; test `LoggingEmailBackend` by instantiating it directly with a locmem inner backend.
- Existing suite is 181 tests, all green — keep it green.
- Admin models must be read-only per spec (catalogue: no add/edit/delete; log: no add/edit, delete allowed).
- New admin models must be added to the Jazzmin icon map at `config/settings.py:354` (`JAZZMIN_SETTINGS["icons"]`), or the admin sidebar errors.
- Commit after each task.

---

### Task 1: Extract fixed-email wording into shared builders (anti-drift prep)

Extract the four fixed emails' subject/body into module-level constants/builders so both the sender and the catalogue import the same strings.

**Files:**
- Modify: `apps/messaging/tasks.py` (no-contact + sponsor reminders)
- Modify: `apps/moderation/service.py:644-678` (`_alert_staff`)
- Modify: `apps/users/auth_views.py:16-50` (`PasswordResetRequestView`)
- Test: `apps/notifications/tests/test_email_wording.py`

**Interfaces:**
- Produces:
  - `apps.messaging.tasks.NO_CONTACT_REMINDER_SUBJECT: str`, `build_no_contact_body(first_name: str) -> str`
  - `apps.messaging.tasks.SPONSOR_UPDATE_SUBJECT: str`, `build_sponsor_update_body(first_name: str, sponsor_name: str) -> str`
  - `apps.moderation.service.build_moderation_alert(sender_name: str, sender_email: str, term: str, admin_url: str, message_pk) -> tuple[str, str]` (subject, body)
  - `apps.users.auth_views.PASSWORD_RESET_SUBJECT: str`, `build_password_reset_body(first_name: str, reset_url: str) -> str`

- [ ] **Step 1: Write the failing test**

Create `apps/notifications/tests/test_email_wording.py`:

```python
from django.test import TestCase

class FixedEmailBuildersTests(TestCase):
    def test_no_contact_builder(self):
        from apps.messaging.tasks import NO_CONTACT_REMINDER_SUBJECT, build_no_contact_body
        self.assertEqual(NO_CONTACT_REMINDER_SUBJECT, 'SPT Mentoring – Time to connect!')
        body = build_no_contact_body('Sam')
        self.assertIn('Hi Sam,', body)
        self.assertIn("haven't been in touch recently", body)

    def test_sponsor_builder(self):
        from apps.messaging.tasks import SPONSOR_UPDATE_SUBJECT, build_sponsor_update_body
        self.assertEqual(SPONSOR_UPDATE_SUBJECT, 'SPT Scholarships – Time to update your sponsor')
        body = build_sponsor_update_body('Sam', 'Acme Trust')
        self.assertIn('Hi Sam,', body)
        self.assertIn('Acme Trust', body)

    def test_moderation_alert_builder(self):
        from apps.moderation.service import build_moderation_alert
        subject, body = build_moderation_alert('Al Ice', 'al@x.com', 'badword',
                                               'https://x/admin/msg/5/', 5)
        self.assertEqual(subject, '[SPT Moderation] Flagged message requires review (#5)')
        self.assertIn('Al Ice (al@x.com)', body)
        self.assertIn('badword', body)

    def test_password_reset_builder(self):
        from apps.users.auth_views import PASSWORD_RESET_SUBJECT, build_password_reset_body
        self.assertEqual(PASSWORD_RESET_SUBJECT, 'Reset your password — Arkwright Mentoring')
        body = build_password_reset_body('Sam', 'https://x/reset-password/u/t')
        self.assertIn('Hi Sam,', body)
        self.assertIn('https://x/reset-password/u/t', body)
        self.assertIn('valid for 3 days', body)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_wording --verbosity=2`
Expected: FAIL with `ImportError`/`cannot import name`.

- [ ] **Step 3: Add builders and refactor senders**

In `apps/messaging/tasks.py`, add near the top (after imports):

```python
NO_CONTACT_REMINDER_SUBJECT = 'SPT Mentoring – Time to connect!'
SPONSOR_UPDATE_SUBJECT = 'SPT Scholarships – Time to update your sponsor'


def build_no_contact_body(first_name):
    return (
        f'Hi {first_name},\n\n'
        'It looks like you and your mentoring partner haven\'t been in touch recently. '
        'Please log in to the SPT Mentoring Platform and send a message.\n\n'
        'Best regards,\nSPT Mentoring Team'
    )


def build_sponsor_update_body(first_name, sponsor_name):
    return (
        f'Hi {first_name},\n\n'
        f'Your sponsor {sponsor_name} is due an update from you. '
        'Please log in to the platform and send them an update on your progress.\n\n'
        'Best regards,\nSPT Scholarships Team'
    )
```

Then in `send_no_contact_reminders`, replace the inline `subject=...`/`message=...` with:
```python
                    send_mail(
                        subject=NO_CONTACT_REMINDER_SUBJECT,
                        message=build_no_contact_body(user.first_name),
                        from_email=settings.MENTORING_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
```
And in `send_sponsor_update_reminders`, replace with:
```python
                send_mail(
                    subject=SPONSOR_UPDATE_SUBJECT,
                    message=build_sponsor_update_body(scholar.first_name, profile.sponsor.full_name),
                    from_email=settings.SCHOLARSHIPS_FROM_EMAIL,
                    recipient_list=[scholar.email],
                    fail_silently=True,
                )
```

In `apps/moderation/service.py`, add a module-level function above the `ModerationService` class:

```python
def build_moderation_alert(sender_name, sender_email, triggered_term, admin_url, message_pk):
    subject = f'[SPT Moderation] Flagged message requires review (#{message_pk})'
    body = (
        f'A message has been flagged for review.\n\n'
        f'Sender:       {sender_name} ({sender_email})\n'
        f'Triggered by: "{triggered_term}"\n'
        f'Review it here: {admin_url}\n'
    )
    return subject, body
```

Then in `_alert_staff`, replace the inline `subject = ...`/`body = (...)` block with:
```python
        subject, body = build_moderation_alert(
            message.sender.full_name, message.sender.email, triggered_term, admin_url, message.pk,
        )
```

In `apps/users/auth_views.py`, add near the top (after imports):

```python
PASSWORD_RESET_SUBJECT = 'Reset your password — Arkwright Mentoring'


def build_password_reset_body(first_name, reset_url):
    return (
        f'Hi {first_name},\n\n'
        f'You requested a password reset for your Arkwright Mentoring account.\n\n'
        f'Click the link below to choose a new password:\n\n'
        f'{reset_url}\n\n'
        f'This link is valid for 3 days. If you did not request this, you can safely ignore this email.\n\n'
        f'The Arkwright Mentoring team'
    )
```

Then in `PasswordResetRequestView.post`, replace the `send_mail(subject=..., message=(...))` args with:
```python
        send_mail(
            subject=PASSWORD_RESET_SUBJECT,
            message=build_password_reset_body(user.first_name, reset_url),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_wording apps.messaging apps.moderation apps.users --verbosity=1`
Expected: PASS (and no regressions — the reminder/moderation/reset tests still pass because output is unchanged).

- [ ] **Step 5: Commit**

```bash
git add apps/messaging/tasks.py apps/moderation/service.py apps/users/auth_views.py apps/notifications/tests/test_email_wording.py
git commit -m "refactor(email): extract fixed email wording into shared builders"
```

---

### Task 2: Email catalogue registry

**Files:**
- Create: `apps/notifications/email_catalogue.py`
- Test: `apps/notifications/tests/test_email_catalogue.py`

**Interfaces:**
- Consumes: builders/constants from Task 1.
- Produces:
  - `EmailSpec` dataclass with fields `key, name, trigger, recipients, subject, body, debounced, source, notes`
  - `EMAIL_CATALOGUE: list[EmailSpec]` (8 entries, keys per spec table)
  - `infer_category(subject: str) -> str` (returns a catalogue key or `''`)

- [ ] **Step 1: Write the failing test**

Create `apps/notifications/tests/test_email_catalogue.py`:

```python
from django.test import TestCase

class EmailCatalogueTests(TestCase):
    def test_keys_unique_and_complete(self):
        from apps.notifications.email_catalogue import EMAIL_CATALOGUE
        keys = [e.key for e in EMAIL_CATALOGUE]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), {
            'message', 'scholar_forum_post', 'notification_digest', 'mass_message',
            'no_contact_reminder', 'sponsor_update_reminder', 'moderation_alert', 'password_reset',
        })

    def test_fixed_entries_use_shared_constants(self):
        from apps.notifications.email_catalogue import EMAIL_CATALOGUE
        from apps.messaging.tasks import NO_CONTACT_REMINDER_SUBJECT
        from apps.users.auth_views import PASSWORD_RESET_SUBJECT
        by_key = {e.key: e for e in EMAIL_CATALOGUE}
        self.assertEqual(by_key['no_contact_reminder'].subject, NO_CONTACT_REMINDER_SUBJECT)
        self.assertEqual(by_key['password_reset'].subject, PASSWORD_RESET_SUBJECT)

    def test_infer_category(self):
        from apps.notifications.email_catalogue import infer_category
        self.assertEqual(infer_category('New message from Alice Scholar'), 'message')
        self.assertEqual(infer_category('You have 4 new notifications on SPT Mentoring'), 'notification_digest')
        self.assertEqual(infer_category('Reset your password — Arkwright Mentoring'), 'password_reset')
        self.assertEqual(infer_category('Bob Mentor posted in the forum'), 'scholar_forum_post')
        self.assertEqual(infer_category('Some random admin broadcast'), '')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_catalogue --verbosity=2`
Expected: FAIL with `ModuleNotFoundError: apps.notifications.email_catalogue`.

- [ ] **Step 3: Write the registry**

Create `apps/notifications/email_catalogue.py`:

```python
"""Single source of truth for the emails the platform sends (read-only catalogue)."""
from dataclasses import dataclass, field

from apps.messaging.tasks import NO_CONTACT_REMINDER_SUBJECT, SPONSOR_UPDATE_SUBJECT
from apps.users.auth_views import PASSWORD_RESET_SUBJECT


@dataclass(frozen=True)
class EmailSpec:
    key: str
    name: str
    trigger: str
    recipients: str
    subject: str
    body: str
    debounced: bool = False
    source: str = ''
    notes: str = ''


EMAIL_CATALOGUE = [
    EmailSpec(
        key='message', name='New message',
        trigger='Another user sends you a direct/group message',
        recipients='Message recipient(s)',
        subject='New message from {sender name}',
        body='{message excerpt}\n\n{link to /messages}',
        debounced=True, source='apps/messaging/signals.py + apps/notifications/emails.py',
        notes='If 2+ notifications are pending in the debounce window they are combined into a notification_digest instead.',
    ),
    EmailSpec(
        key='scholar_forum_post', name='Scholar forum post',
        trigger='Your matched scholar posts in a forum you can see',
        recipients='Matched mentor(s) of the posting scholar',
        subject='{scholar name} posted in the forum',
        body='{thread title}: {post excerpt}\n\n{link to /forums}',
        debounced=True, source='apps/forums/services.py',
    ),
    EmailSpec(
        key='notification_digest', name='Notification digest',
        trigger='Debounce window closes with 2+ unread pending notifications',
        recipients='The recipient of the batched notifications',
        subject='You have {N} new notifications on SPT Mentoring',
        body='Hi {first name},\n\nYou have {counts} on SPT Mentoring:\n\n- {title}\n  {link}\n...\n\nLog in to the SPT Mentoring Platform to read them.',
        source='apps/notifications/digest.py',
    ),
    EmailSpec(
        key='mass_message', name='Mass message',
        trigger='Admin sends a broadcast from the Mass Message admin',
        recipients='All users matching the broadcast filters',
        subject='{admin-authored subject}',
        body='{admin-authored body}',
        source='apps/messaging/tasks.py:send_mass_message_task',
        notes='Subject/body are authored by the admin per broadcast; from-address is the broadcast sender.',
    ),
    EmailSpec(
        key='no_contact_reminder', name='No-contact reminder',
        trigger='A scholar/mentor pair has not messaged for NO_CONTACT_REMINDER_DAYS (Beat, daily 9am)',
        recipients='Both members of the pair (if email on)',
        subject=NO_CONTACT_REMINDER_SUBJECT,
        body="Hi {first name},\n\nIt looks like you and your mentoring partner haven't been in touch recently. Please log in to the SPT Mentoring Platform and send a message.\n\nBest regards,\nSPT Mentoring Team",
        source='apps/messaging/tasks.py:send_no_contact_reminders',
    ),
    EmailSpec(
        key='sponsor_update_reminder', name='Sponsor update reminder',
        trigger='A scholar is overdue to update their sponsor (Beat, Monday 9:30am)',
        recipients='The scholar (if email on)',
        subject=SPONSOR_UPDATE_SUBJECT,
        body='Hi {first name},\n\nYour sponsor {sponsor name} is due an update from you. Please log in to the platform and send them an update on your progress.\n\nBest regards,\nSPT Scholarships Team',
        source='apps/messaging/tasks.py:send_sponsor_update_reminders',
    ),
    EmailSpec(
        key='moderation_alert', name='Moderation alert',
        trigger='A message or forum post is flagged for review',
        recipients='All active staff/admin users',
        subject='[SPT Moderation] Flagged message requires review (#{id})',
        body='A message has been flagged for review.\n\nSender:       {name} ({email})\nTriggered by: "{term}"\nPreview:      {first 200 chars of message}\nReview it here: {admin url}',
        source='apps/moderation/service.py:_alert_staff',
    ),
    EmailSpec(
        key='password_reset', name='Password reset',
        trigger='A user requests a password reset',
        recipients='The requesting user',
        subject=PASSWORD_RESET_SUBJECT,
        body='Hi {first name},\n\nYou requested a password reset for your Arkwright Mentoring account.\n\nClick the link below to choose a new password:\n\n{reset url}\n\nThis link is valid for 3 days. If you did not request this, you can safely ignore this email.\n\nThe Arkwright Mentoring team',
        source='apps/users/auth_views.py:PasswordResetRequestView',
    ),
]


# (subject substring, catalogue key) — first match wins. Order matters.
_CATEGORY_MATCHERS = [
    ('[SPT Moderation] Flagged message', 'moderation_alert'),
    ('Reset your password', 'password_reset'),
    ('new notifications on SPT Mentoring', 'notification_digest'),
    ('New message from', 'message'),
    ('posted in the forum', 'scholar_forum_post'),
    (NO_CONTACT_REMINDER_SUBJECT, 'no_contact_reminder'),
    (SPONSOR_UPDATE_SUBJECT, 'sponsor_update_reminder'),
]


def infer_category(subject):
    """Best-effort classify a sent email's subject to a catalogue key ('' if unknown)."""
    subject = subject or ''
    for needle, key in _CATEGORY_MATCHERS:
        if needle in subject:
            return key
    return ''
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_catalogue --verbosity=2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/notifications/email_catalogue.py apps/notifications/tests/test_email_catalogue.py
git commit -m "feat(notifications): email catalogue registry + category inference"
```

---

### Task 3: EmailCatalogueEntry model

**Files:**
- Modify: `apps/notifications/models.py` (append model)
- Create: migration (generated)
- Test: `apps/notifications/tests/test_catalogue_sync.py` (model import only in this task)

**Interfaces:**
- Produces: `apps.notifications.models.EmailCatalogueEntry` with fields
  `key (unique), name, trigger, recipients, subject, body, debounced (bool), source, notes, updated_at`.

- [ ] **Step 1: Write the failing test**

Create `apps/notifications/tests/test_catalogue_sync.py`:

```python
from django.test import TestCase

class EmailCatalogueEntryModelTests(TestCase):
    def test_can_create_entry(self):
        from apps.notifications.models import EmailCatalogueEntry
        e = EmailCatalogueEntry.objects.create(
            key='k', name='n', trigger='t', recipients='r',
            subject='s', body='b', debounced=False, source='src',
        )
        self.assertEqual(str(e), 'n')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_catalogue_sync --verbosity=2`
Expected: FAIL with `ImportError: cannot import name 'EmailCatalogueEntry'`.

- [ ] **Step 3: Add the model**

Append to `apps/notifications/models.py`:

```python
class EmailCatalogueEntry(models.Model):
    """Read-only projection of the code email catalogue (see email_catalogue.py).

    Rebuilt by `manage.py sync_email_catalogue`; do not edit in admin.
    """
    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    trigger = models.CharField(max_length=300)
    recipients = models.CharField(max_length=200)
    subject = models.CharField(max_length=300)
    body = models.TextField()
    debounced = models.BooleanField(default=False)
    source = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Email Catalogue Entry'
        verbose_name_plural = 'Email Catalogue'
        ordering = ['name']

    def __str__(self):
        return self.name
```

- [ ] **Step 4: Make migration, migrate, run test**

Run:
```bash
docker exec spt-mentoring-backend-1 python manage.py makemigrations notifications
docker exec spt-mentoring-backend-1 python manage.py migrate
docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_catalogue_sync --verbosity=2
```
Expected: migration `000X_emailcatalogueentry` created and applied; test PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/notifications/models.py apps/notifications/migrations/ apps/notifications/tests/test_catalogue_sync.py
git commit -m "feat(notifications): EmailCatalogueEntry model"
```

---

### Task 4: sync_email_catalogue management command

**Files:**
- Create: `apps/notifications/management/commands/sync_email_catalogue.py`
- Modify: `apps/notifications/tests/test_catalogue_sync.py` (add sync tests)

**Interfaces:**
- Consumes: `EMAIL_CATALOGUE` (Task 2), `EmailCatalogueEntry` (Task 3).
- Produces: `python manage.py sync_email_catalogue` — idempotent upsert + prune.

- [ ] **Step 1: Write the failing tests**

Append to `apps/notifications/tests/test_catalogue_sync.py`:

```python
from django.core.management import call_command
from django.test import TestCase as _TC

class SyncCommandTests(_TC):
    def test_sync_populates_and_is_idempotent(self):
        from apps.notifications.models import EmailCatalogueEntry
        from apps.notifications.email_catalogue import EMAIL_CATALOGUE
        call_command('sync_email_catalogue')
        self.assertEqual(EmailCatalogueEntry.objects.count(), len(EMAIL_CATALOGUE))
        call_command('sync_email_catalogue')  # again
        self.assertEqual(EmailCatalogueEntry.objects.count(), len(EMAIL_CATALOGUE))

    def test_sync_prunes_stale(self):
        from apps.notifications.models import EmailCatalogueEntry
        EmailCatalogueEntry.objects.create(key='ghost', name='Ghost', trigger='t',
                                            recipients='r', subject='s', body='b')
        call_command('sync_email_catalogue')
        self.assertFalse(EmailCatalogueEntry.objects.filter(key='ghost').exists())

    def test_sync_updates_changed_fields(self):
        from apps.notifications.models import EmailCatalogueEntry
        call_command('sync_email_catalogue')
        EmailCatalogueEntry.objects.filter(key='password_reset').update(subject='WRONG')
        call_command('sync_email_catalogue')
        self.assertNotEqual(
            EmailCatalogueEntry.objects.get(key='password_reset').subject, 'WRONG')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_catalogue_sync.SyncCommandTests --verbosity=2`
Expected: FAIL with `Unknown command: 'sync_email_catalogue'`.

- [ ] **Step 3: Write the command**

Create `apps/notifications/management/commands/sync_email_catalogue.py`:

```python
from django.core.management.base import BaseCommand

from apps.notifications.email_catalogue import EMAIL_CATALOGUE
from apps.notifications.models import EmailCatalogueEntry


class Command(BaseCommand):
    help = 'Rebuild the EmailCatalogueEntry table from email_catalogue.EMAIL_CATALOGUE.'

    def handle(self, *args, **options):
        keys = set()
        for spec in EMAIL_CATALOGUE:
            keys.add(spec.key)
            EmailCatalogueEntry.objects.update_or_create(
                key=spec.key,
                defaults=dict(
                    name=spec.name, trigger=spec.trigger, recipients=spec.recipients,
                    subject=spec.subject, body=spec.body, debounced=spec.debounced,
                    source=spec.source, notes=spec.notes,
                ),
            )
        removed, _ = EmailCatalogueEntry.objects.exclude(key__in=keys).delete()
        self.stdout.write(self.style.SUCCESS(
            f'Synced {len(EMAIL_CATALOGUE)} catalogue entries ({removed} stale removed).'))
```

Create empty `apps/notifications/management/__init__.py` and `apps/notifications/management/commands/__init__.py` if they do not already exist.

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_catalogue_sync --verbosity=2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/notifications/management/ apps/notifications/tests/test_catalogue_sync.py
git commit -m "feat(notifications): sync_email_catalogue command"
```

---

### Task 5: EmailCatalogueEntry admin (read-only) + icon

**Files:**
- Modify: `apps/notifications/admin.py`
- Modify: `config/settings.py:354` (Jazzmin icons)
- Test: `apps/notifications/tests/test_catalogue_admin.py`

- [ ] **Step 1: Write the failing test**

Create `apps/notifications/tests/test_catalogue_admin.py`:

```python
from django.contrib import admin
from django.test import TestCase

class CatalogueAdminTests(TestCase):
    def test_registered_and_read_only(self):
        from apps.notifications.models import EmailCatalogueEntry
        self.assertIn(EmailCatalogueEntry, admin.site._registry)
        ma = admin.site._registry[EmailCatalogueEntry]
        self.assertFalse(ma.has_add_permission(request=None))
        self.assertFalse(ma.has_delete_permission(request=None))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_catalogue_admin --verbosity=2`
Expected: FAIL (`EmailCatalogueEntry` not in registry).

- [ ] **Step 3: Register read-only admin**

Append to `apps/notifications/admin.py`:

```python
from .models import EmailCatalogueEntry


@admin.register(EmailCatalogueEntry)
class EmailCatalogueEntryAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'recipients', 'debounced')
    list_filter = ('debounced',)
    search_fields = ('name', 'key', 'subject', 'body')
    readonly_fields = ('key', 'name', 'trigger', 'recipients', 'subject', 'body',
                       'debounced', 'source', 'notes', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # view-only detail page

    def has_delete_permission(self, request, obj=None):
        return False
```

Note: the existing `admin.py` already does `from .models import Notification` and `@admin.register`; keep imports consistent (you may merge the model import into the existing import line).

Add to `config/settings.py` inside `JAZZMIN_SETTINGS["icons"]` (near line 382):
```python
        "notifications.Notification":      "fas fa-bell",
        "notifications.PushSubscription":  "fas fa-mobile-alt",
        "notifications.EmailCatalogueEntry": "fas fa-book",
```
(Only add lines that are not already present.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications --verbosity=1 && docker exec spt-mentoring-backend-1 python manage.py check`
Expected: PASS; system check clean.

- [ ] **Step 5: Commit**

```bash
git add apps/notifications/admin.py config/settings.py apps/notifications/tests/test_catalogue_admin.py
git commit -m "feat(notifications): read-only EmailCatalogueEntry admin + icon"
```

---

### Task 6: EmailLog model

**Files:**
- Modify: `apps/notifications/models.py`
- Create: migration (generated)
- Test: `apps/notifications/tests/test_email_log.py` (model creation)

**Interfaces:**
- Produces: `apps.notifications.models.EmailLog` with fields
  `to, from_email, subject, body (Text), status ('sent'|'failed'), error, category, created_at (indexed)`
  and `EmailLog.Status` choices.

- [ ] **Step 1: Write the failing test**

Create `apps/notifications/tests/test_email_log.py`:

```python
from django.test import TestCase

class EmailLogModelTests(TestCase):
    def test_create(self):
        from apps.notifications.models import EmailLog
        log = EmailLog.objects.create(
            to='a@x.com', from_email='b@x.com', subject='Hi', body='Body',
            status=EmailLog.Status.SENT, category='message',
        )
        self.assertEqual(log.status, 'sent')
        self.assertIn('a@x.com', str(log))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_log --verbosity=2`
Expected: FAIL (`cannot import name 'EmailLog'`).

- [ ] **Step 3: Add the model**

Append to `apps/notifications/models.py`:

```python
class EmailLog(models.Model):
    """Audit record of an email the system attempted to send (see LoggingEmailBackend)."""
    class Status(models.TextChoices):
        SENT = 'sent', _('Sent')
        FAILED = 'failed', _('Failed')

    to = models.CharField(max_length=500)
    from_email = models.CharField(max_length=254, blank=True)
    subject = models.CharField(max_length=500)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SENT)
    error = models.TextField(blank=True)
    category = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Email Log'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} → {self.to} [{self.status}]'
```

- [ ] **Step 4: Make migration, migrate, run test**

Run:
```bash
docker exec spt-mentoring-backend-1 python manage.py makemigrations notifications
docker exec spt-mentoring-backend-1 python manage.py migrate
docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_log --verbosity=2
```
Expected: migration created + applied; test PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/notifications/models.py apps/notifications/migrations/ apps/notifications/tests/test_email_log.py
git commit -m "feat(notifications): EmailLog model"
```

---

### Task 7: LoggingEmailBackend + settings wiring

**Files:**
- Create: `config/logging_email_backend.py`
- Modify: `config/settings.py` (EMAIL section ~line 210)
- Modify: `apps/notifications/tests/test_email_log.py` (backend tests)

**Interfaces:**
- Consumes: `EmailLog` (Task 6), `infer_category` (Task 2).
- Produces: `config.logging_email_backend.LoggingEmailBackend` (a `BaseEmailBackend`).

- [ ] **Step 1: Write the failing tests**

Append to `apps/notifications/tests/test_email_log.py`:

```python
from django.test import TestCase as _TC, override_settings
from django.core.mail import EmailMessage

INNER = 'django.core.mail.backends.locmem.EmailBackend'

@override_settings(LOGGED_EMAIL_BACKEND=INNER)
class LoggingBackendTests(_TC):
    def _backend(self):
        from config.logging_email_backend import LoggingEmailBackend
        return LoggingEmailBackend()

    def test_logs_and_delivers(self):
        from apps.notifications.models import EmailLog
        from django.core import mail
        mail.outbox = []
        msg = EmailMessage('New message from Alice Scholar', 'Body here',
                           'from@x.com', ['to@x.com'])
        sent = self._backend().send_messages([msg])
        self.assertEqual(sent, 1)
        self.assertEqual(len(mail.outbox), 1)          # delegated to inner
        log = EmailLog.objects.get()
        self.assertEqual(log.to, 'to@x.com')
        self.assertEqual(log.subject, 'New message from Alice Scholar')
        self.assertEqual(log.status, 'sent')
        self.assertEqual(log.category, 'message')      # inferred

    @override_settings(LOGGED_EMAIL_BACKEND='config.logging_email_backend._AlwaysFailBackend')
    def test_send_failure_is_recorded(self):
        from apps.notifications.models import EmailLog
        msg = EmailMessage('Reset your password — Arkwright Mentoring', 'b', 'f@x.com', ['t@x.com'])
        try:
            self._backend().send_messages([msg])
        except Exception:
            pass
        log = EmailLog.objects.get()
        self.assertEqual(log.status, 'failed')
        self.assertTrue(log.error)

    def test_logging_error_does_not_block_send(self):
        from django.core import mail
        from unittest.mock import patch
        mail.outbox = []
        msg = EmailMessage('Hi', 'b', 'f@x.com', ['t@x.com'])
        with patch('apps.notifications.models.EmailLog.objects.create', side_effect=Exception('db down')):
            self._backend().send_messages([msg])
        self.assertEqual(len(mail.outbox), 1)          # email still delivered
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_log.LoggingBackendTests --verbosity=2`
Expected: FAIL (`config.logging_email_backend` missing).

- [ ] **Step 3: Write the backend**

Create `config/logging_email_backend.py`:

```python
"""Email backend that records every message to EmailLog, then delegates to the real backend."""
import logging

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

DEFAULT_INNER = 'config.smtp2go_backend.SMTP2GOEmailBackend'


class _AlwaysFailBackend(BaseEmailBackend):
    """Test helper: raises on send."""
    def send_messages(self, email_messages):
        raise RuntimeError('simulated send failure')


class LoggingEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        inner_path = getattr(settings, 'LOGGED_EMAIL_BACKEND', DEFAULT_INNER)
        self._inner = import_string(inner_path)(fail_silently=fail_silently, **kwargs)

    def send_messages(self, email_messages):
        from apps.notifications.models import EmailLog
        from apps.notifications.email_catalogue import infer_category

        if not email_messages:
            return 0

        error_text = ''
        status = EmailLog.Status.SENT
        try:
            sent = self._inner.send_messages(email_messages)
        except Exception as exc:  # record failure, then re-raise unless fail_silently
            status = EmailLog.Status.FAILED
            error_text = repr(exc)
            self._log(email_messages, status, error_text)
            if self.fail_silently:
                return 0
            raise

        # send_messages returns number sent (may be None); treat falsy as failed.
        if not sent:
            status = EmailLog.Status.FAILED
        self._log(email_messages, status, error_text)
        return sent

    def _log(self, email_messages, status, error_text):
        from apps.notifications.models import EmailLog
        from apps.notifications.email_catalogue import infer_category
        for msg in email_messages:
            try:
                EmailLog.objects.create(
                    to=', '.join(msg.to or []),
                    from_email=msg.from_email or '',
                    subject=msg.subject or '',
                    body=msg.body or '',
                    status=status,
                    error=error_text,
                    category=infer_category(msg.subject or ''),
                )
            except Exception:
                # Logging must never break delivery.
                logger.exception('Failed to write EmailLog for message to %s', msg.to)
```

In `config/settings.py`, change the EMAIL section (around line 211):
```python
EMAIL_BACKEND = config('EMAIL_BACKEND', default='config.logging_email_backend.LoggingEmailBackend')
LOGGED_EMAIL_BACKEND = config('LOGGED_EMAIL_BACKEND', default='config.smtp2go_backend.SMTP2GOEmailBackend')
```
(Leave the other EMAIL_* settings as-is. In prod `.env`, ensure `EMAIL_BACKEND` is either unset or set to the logging backend, and `LOGGED_EMAIL_BACKEND` points at SMTP2GO.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_log --verbosity=2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/logging_email_backend.py config/settings.py apps/notifications/tests/test_email_log.py
git commit -m "feat(email): LoggingEmailBackend records every send to EmailLog"
```

---

### Task 8: EmailLog admin (read-only, delete allowed) + icon

**Files:**
- Modify: `apps/notifications/admin.py`
- Modify: `config/settings.py:354` (icon)
- Test: `apps/notifications/tests/test_email_log_admin.py`

- [ ] **Step 1: Write the failing test**

Create `apps/notifications/tests/test_email_log_admin.py`:

```python
from django.contrib import admin
from django.test import TestCase

class EmailLogAdminTests(TestCase):
    def test_registered_readonly_but_deletable(self):
        from apps.notifications.models import EmailLog
        self.assertIn(EmailLog, admin.site._registry)
        ma = admin.site._registry[EmailLog]
        self.assertFalse(ma.has_add_permission(request=None))
        self.assertFalse(ma.has_change_permission(request=None))
        self.assertTrue(ma.has_delete_permission(request=None))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_log_admin --verbosity=2`
Expected: FAIL (`EmailLog` not registered).

- [ ] **Step 3: Register admin**

Append to `apps/notifications/admin.py`:

```python
from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'to', 'subject', 'category', 'status')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('to', 'subject')
    readonly_fields = ('to', 'from_email', 'subject', 'body', 'status', 'error',
                       'category', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True
```

Add to `config/settings.py` `JAZZMIN_SETTINGS["icons"]`:
```python
        "notifications.EmailLog": "fas fa-inbox",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications --verbosity=1 && docker exec spt-mentoring-backend-1 python manage.py check`
Expected: PASS; check clean.

- [ ] **Step 5: Commit**

```bash
git add apps/notifications/admin.py config/settings.py apps/notifications/tests/test_email_log_admin.py
git commit -m "feat(notifications): read-only EmailLog admin + icon"
```

---

### Task 9: Auto-prune task + beat schedule + setting

**Files:**
- Modify: `apps/notifications/tasks.py` (add `purge_email_logs_task`)
- Modify: `config/celery.py` (beat schedule)
- Modify: `config/settings.py` (add `EMAIL_LOG_RETENTION_DAYS`)
- Test: `apps/notifications/tests/test_email_log_purge.py`

**Interfaces:**
- Consumes: `EmailLog` (Task 6).
- Produces: `apps.notifications.tasks.purge_email_logs_task()`.

- [ ] **Step 1: Write the failing test**

Create `apps/notifications/tests/test_email_log_purge.py`:

```python
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone

@override_settings(EMAIL_LOG_RETENTION_DAYS=90)
class PurgeTests(TestCase):
    def test_purges_only_old_rows(self):
        from apps.notifications.models import EmailLog
        from apps.notifications.tasks import purge_email_logs_task
        old = EmailLog.objects.create(to='a@x.com', subject='s', body='b')
        EmailLog.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=120))
        recent = EmailLog.objects.create(to='b@x.com', subject='s', body='b')

        purge_email_logs_task()

        self.assertFalse(EmailLog.objects.filter(pk=old.pk).exists())
        self.assertTrue(EmailLog.objects.filter(pk=recent.pk).exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_log_purge --verbosity=2`
Expected: FAIL (`cannot import name 'purge_email_logs_task'`).

- [ ] **Step 3: Add task, schedule, setting**

Append to `apps/notifications/tasks.py`:

```python
@shared_task
def purge_email_logs_task():
    """Delete EmailLog rows older than settings.EMAIL_LOG_RETENTION_DAYS."""
    from datetime import timedelta
    from django.conf import settings
    from django.utils import timezone
    from .models import EmailLog

    days = getattr(settings, 'EMAIL_LOG_RETENTION_DAYS', 90)
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = EmailLog.objects.filter(created_at__lt=cutoff).delete()
    logger.info('purge_email_logs_task: deleted %s rows older than %s days', deleted, days)
    return deleted
```

Add to `config/settings.py` (near the notification-email debounce settings):
```python
EMAIL_LOG_RETENTION_DAYS = config('EMAIL_LOG_RETENTION_DAYS', default=90, cast=int)
```

Add to `config/celery.py` `beat_schedule`:
```python
    'purge-email-logs-daily': {
        'task': 'apps.notifications.tasks.purge_email_logs_task',
        'schedule': crontab(hour=3, minute=15),  # daily 03:15
    },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker exec spt-mentoring-backend-1 python manage.py test apps.notifications.tests.test_email_log_purge --verbosity=2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/notifications/tasks.py config/celery.py config/settings.py apps/notifications/tests/test_email_log_purge.py
git commit -m "feat(notifications): auto-prune EmailLog via daily Beat task"
```

---

### Task 10: Full-suite verification + deploy

**Files:** none (verification + operational steps).

- [ ] **Step 1: Run the entire suite**

Run: `docker exec spt-mentoring-backend-1 python manage.py test --verbosity=1`
Expected: all tests PASS (181 prior + new), 0 failures/errors.

- [ ] **Step 2: Check migrations + system check**

Run:
```bash
docker exec spt-mentoring-backend-1 python manage.py makemigrations --check --dry-run
docker exec spt-mentoring-backend-1 python manage.py check
```
Expected: "No changes detected"; system check clean.

- [ ] **Step 3: Seed the catalogue**

Run: `docker exec spt-mentoring-backend-1 python manage.py sync_email_catalogue`
Expected: "Synced 8 catalogue entries (0 stale removed)."

- [ ] **Step 4: Set prod env + restart**

Ensure prod `.env` has `EMAIL_BACKEND=config.logging_email_backend.LoggingEmailBackend` and `LOGGED_EMAIL_BACKEND=config.smtp2go_backend.SMTP2GOEmailBackend`. Then:
```bash
docker restart spt-mentoring-backend-1 spt-mentoring-worker-1 spt-mentoring-beat-1
```
Verify beat now lists `purge-email-logs-daily`, worker registers `purge_email_logs_task`, and a test email (from a controlled account) appears in `/admin` → Email Log with the right category, subject and body.

- [ ] **Step 5: Commit any final docs**

```bash
git add -A docs/
git commit -m "docs(notifications): email catalogue + log delivered"
```

## Self-Review

- **Spec coverage:** catalogue registry (T2), model (T3), sync (T4), read-only admin (T5); log model (T6), capture backend + settings (T7), read-only+deletable admin (T8), auto-prune (T9); anti-drift extraction (T1) + anti-drift test (T2); category inference (T2/T7); deployment + icon map (T5/T8/T10). All spec sections covered.
- **Placeholders:** none — every step has concrete code/commands.
- **Type consistency:** `EmailSpec` fields, `EmailLog.Status`, `infer_category` signature, `LoggingEmailBackend.send_messages` return, and task names are consistent across tasks.
