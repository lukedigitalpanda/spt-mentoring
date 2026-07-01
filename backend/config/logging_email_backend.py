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
