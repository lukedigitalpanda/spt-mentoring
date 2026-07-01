"""
Celery tasks for the notifications app.

The debounced notification-email batches (N-3) are flushed by a periodic task;
see apps.notifications.digest for the mechanism.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def flush_notification_email_digests_task():
    """Periodic task: send summary emails for every recipient whose debounce
    window has closed.  Scheduled via Celery Beat (see config/celery.py)."""
    from .digest import flush_due_email_digests
    flush_due_email_digests()


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
