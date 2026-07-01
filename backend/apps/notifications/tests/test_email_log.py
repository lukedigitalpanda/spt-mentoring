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
