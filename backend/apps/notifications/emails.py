"""
Per-notification email dispatch.

Browser push is dispatched by a post_save signal on Notification (see
signals.py).  This module is the equivalent path for email: given a
Notification, decide whether the recipient should be emailed and, if so, send
one email.  Only notification types in EMAILABLE_TYPES generate email — other
types (sessions, news, admin/system alerts) keep their existing behaviour and
are never emailed from here.

Failures are logged with the recipient and notification type; they are never
swallowed silently.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


# Notification types that generate an email to the recipient (if they have
# email notifications enabled).  Kept explicit so we never start emailing about
# a type that previously only produced in-app/push notifications.
EMAILABLE_TYPES = {
    Notification.Type.MESSAGE,
    Notification.Type.SCHOLAR_FORUM_POST,
    Notification.Type.FORUM_REPLY,
}


def absolute_link(link):
    """Turn a relative frontend path into a full, clickable URL."""
    link = link or ''
    if link.startswith('/'):
        return f'{settings.FRONTEND_URL}{link}'
    return link


def send_notification_email(notification):
    """Send a single email for ``notification`` if the recipient wants it.

    Returns True if an email was sent, False if it was intentionally skipped
    (type not emailable, recipient opted out, or no email address).
    """
    if notification.notification_type not in EMAILABLE_TYPES:
        return False

    user = notification.user
    if not user.notification_email or not user.email:
        return False

    link = absolute_link(notification.link)

    body = notification.body
    if link:
        body = f'{body}\n\n{link}'

    try:
        send_mail(
            subject=notification.title,
            message=body,
            from_email=settings.MENTORING_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            'Failed to send notification email (recipient=%s, type=%s, notification_id=%s)',
            user.email, notification.notification_type, notification.pk,
        )
        return False

    return True
