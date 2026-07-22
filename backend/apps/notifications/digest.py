"""
N-3: debounce / batch notification emails.

A notification email is not sent immediately.  Instead the notification is
marked ``email_pending`` and the recipient's EmailDigest window is opened (or
extended).  A periodic task (flush_due_email_digests) sends one summary email
per recipient when their window closes, skipping anything already read in-app.

Browser push and in-app notifications are untouched — they remain immediate.
Only MESSAGE and SCHOLAR_FORUM_POST notifications are debounced; admin/system
emails (password reset, moderation alerts) go straight through send_mail and
never reach this module.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Notification, EmailDigest
from .emails import EMAILABLE_TYPES, send_notification_email, absolute_link

logger = logging.getLogger(__name__)


def _window():
    return timedelta(seconds=getattr(settings, 'NOTIFICATION_EMAIL_DEBOUNCE_SECONDS', 300))


def _cap():
    return timedelta(seconds=getattr(settings, 'NOTIFICATION_EMAIL_MAX_DELAY_SECONDS', 900))


def queue_notification_email(notification):
    """Queue ``notification`` for a debounced email instead of sending now.

    No-ops (nothing queued) when the type is not emailable, the recipient has
    email notifications off, or has no email address.
    """
    if notification.notification_type not in EMAILABLE_TYPES:
        return

    user = notification.user
    if not user.notification_email or not user.email:
        return

    now = timezone.now()

    with transaction.atomic():
        if not notification.email_pending:
            notification.email_pending = True
            notification.save(update_fields=['email_pending'])

        digest, created = EmailDigest.objects.select_for_update().get_or_create(
            user=user,
            defaults={'window_started_at': now, 'send_after': now + _window()},
        )
        if not created:
            # Slide the window forward, but never past the hard cap.
            capped = min(now + _window(), digest.window_started_at + _cap())
            if capped > digest.send_after:
                digest.send_after = capped
                digest.save(update_fields=['send_after'])


def flush_due_email_digests():
    """Send summary emails for every recipient whose window has closed."""
    now = timezone.now()
    due_ids = list(
        EmailDigest.objects.filter(send_after__lte=now).values_list('pk', flat=True)
    )
    for digest_id in due_ids:
        try:
            _flush_digest(digest_id)
        except Exception:
            logger.exception('Failed to flush email digest %s', digest_id)


def _flush_digest(digest_id):
    with transaction.atomic():
        try:
            digest = EmailDigest.objects.select_for_update().get(pk=digest_id)
        except EmailDigest.DoesNotExist:
            return

        user = digest.user
        pending = list(
            Notification.objects.select_for_update().filter(user=user, email_pending=True)
        )
        pending_ids = [n.pk for n in pending]

        # Only email about notifications the recipient hasn't already read in-app.
        unread = [n for n in pending if not n.is_read]

        if user.notification_email and user.email and unread:
            if len(unread) == 1:
                send_notification_email(unread[0])
            else:
                _send_summary_email(user, unread)

        # Clear the batch (read items are dropped without an email) and close
        # the window.
        Notification.objects.filter(pk__in=pending_ids).update(email_pending=False)
        digest.delete()


def _summary_counts(notifications):
    messages = sum(1 for n in notifications if n.notification_type == Notification.Type.MESSAGE)
    forum = sum(1 for n in notifications if n.notification_type == Notification.Type.SCHOLAR_FORUM_POST)
    parts = []
    if messages:
        parts.append(f'{messages} new message{"s" if messages != 1 else ""}')
    if forum:
        parts.append(f'{forum} new forum post{"s" if forum != 1 else ""}')
    other = len(notifications) - messages - forum
    if other:
        parts.append(f'{other} other notification{"s" if other != 1 else ""}')
    return ' and '.join(parts) if parts else f'{len(notifications)} new notifications'


def _send_summary_email(user, notifications):
    summary = _summary_counts(notifications)
    lines = [f'Hi {user.first_name},', '', f'You have {summary} on SPT Mentoring:', '']
    for n in notifications:
        lines.append(f'- {n.title}')
        link = absolute_link(n.link)
        if link:
            lines.append(f'  {link}')
    lines += ['', 'Log in to the SPT Mentoring Platform to read them.']
    body = '\n'.join(lines)

    try:
        send_mail(
            subject=f'You have {len(notifications)} new notifications on SPT Mentoring',
            message=body,
            from_email=settings.MENTORING_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            'Failed to send digest email (recipient=%s, items=%s)', user.email, len(notifications),
        )
