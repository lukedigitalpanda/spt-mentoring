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
