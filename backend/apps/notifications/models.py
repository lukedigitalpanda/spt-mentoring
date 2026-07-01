"""
In-app notification model for SPT Mentoring Platform.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Type(models.TextChoices):
        SESSION_REQUEST   = 'session_request',   _('Session Request')
        SESSION_CONFIRMED = 'session_confirmed',  _('Session Confirmed')
        SESSION_CANCELLED = 'session_cancelled',  _('Session Cancelled')
        SESSION_REMINDER  = 'session_reminder',   _('Session Reminder')
        SESSION_FEEDBACK  = 'session_feedback',   _('Feedback Requested')
        MESSAGE           = 'message',             _('New Message')
        MATCH             = 'match',               _('New Match')
        FORUM_REPLY       = 'forum_reply',         _('Forum Reply')
        SCHOLAR_FORUM_POST = 'scholar_forum_post', _('Scholar Forum Post')
        SURVEY            = 'survey',              _('New Survey')
        GOAL              = 'goal',                _('Goal Update')
        NEWS_ITEM         = 'news_item',           _('News Published')
        SYSTEM            = 'system',              _('System')

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500)
    link = models.CharField(max_length=200, blank=True, help_text='Frontend URL to navigate to')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # N-3: queued for a debounced email (cleared once the digest is sent).
    email_pending = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'

    def __str__(self):
        return f"[{self.notification_type}] {self.title} → {self.user.full_name}"


class PushSubscription(models.Model):
    """Browser Web Push subscription stored per user/device."""
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='push_subscriptions',
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Push Subscription'

    def __str__(self):
        return f"{self.user.email} – {self.endpoint[:60]}"


class EmailDigest(models.Model):
    """Per-recipient debounce window for notification emails (N-3).

    While a window is open, emailable notifications for the user accumulate
    (Notification.email_pending=True).  ``send_after`` slides forward as new
    notifications arrive, but never past ``window_started_at`` + the configured
    cap, so an email is never held indefinitely.  Persisted so pending batches
    survive a worker restart.
    """
    user = models.OneToOneField(
        'users.User', on_delete=models.CASCADE, related_name='email_digest',
    )
    window_started_at = models.DateTimeField()
    send_after = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = 'Email Digest'

    def __str__(self):
        return f"{self.user.email} – flush after {self.send_after:%Y-%m-%d %H:%M}"


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
