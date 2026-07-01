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
