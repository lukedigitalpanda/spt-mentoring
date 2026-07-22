"""
Tests for sprint item N-3: debounce / batch notification emails.

Push and in-app stay immediate; emails are held in a per-recipient window and
sent as one summary.  State is persisted (EmailDigest + Notification.email_pending)
so it survives a worker restart.

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test apps.notifications --verbosity=2
"""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone

from apps.users.models import User
from apps.notifications.models import Notification


def make_user(email='mentor@example.com', **kwargs):
    defaults = dict(
        username=email.split('@')[0], email=email, first_name='Mentor', last_name='Test',
        role=User.Role.MENTOR, is_active=True, is_verified=True, notification_email=True,
    )
    defaults.update(kwargs)
    return User.objects.create(**defaults)


def make_note(user, ntype=Notification.Type.MESSAGE, title='New message from Alice Scholar',
              body='hi', link='/messages'):
    return Notification.objects.create(
        user=user, notification_type=ntype, title=title, body=body, link=link,
    )


@override_settings(
    FRONTEND_URL='https://mentoring.example.test',
    NOTIFICATION_EMAIL_DEBOUNCE_SECONDS=300,
    NOTIFICATION_EMAIL_MAX_DELAY_SECONDS=900,
)
class EmailDebounceTests(TestCase):

    def setUp(self):
        self.user = make_user()

    # --- queueing --------------------------------------------------------

    def test_queue_does_not_send_immediately(self):
        from apps.notifications.digest import queue_notification_email
        from apps.notifications.models import EmailDigest

        mail.outbox = []
        note = make_note(self.user)
        queue_notification_email(note)

        self.assertEqual(len(mail.outbox), 0)
        note.refresh_from_db()
        self.assertTrue(note.email_pending)
        digest = EmailDigest.objects.get(user=self.user)
        self.assertAlmostEqual(
            digest.send_after, timezone.now() + timedelta(seconds=300),
            delta=timedelta(seconds=10),
        )

    def test_non_emailable_type_not_queued(self):
        from apps.notifications.digest import queue_notification_email
        from apps.notifications.models import EmailDigest

        note = make_note(self.user, ntype=Notification.Type.SYSTEM, title='sys')
        queue_notification_email(note)
        self.assertFalse(EmailDigest.objects.filter(user=self.user).exists())

    def test_opted_out_user_not_queued(self):
        from apps.notifications.digest import queue_notification_email
        from apps.notifications.models import EmailDigest

        self.user.notification_email = False
        self.user.save(update_fields=['notification_email'])
        queue_notification_email(make_note(self.user))
        self.assertFalse(EmailDigest.objects.filter(user=self.user).exists())

    # --- flushing --------------------------------------------------------

    def _flush_now(self):
        """Force any open window to be due, then flush."""
        from apps.notifications.models import EmailDigest
        from apps.notifications.digest import flush_due_email_digests
        EmailDigest.objects.update(send_after=timezone.now() - timedelta(seconds=1))
        flush_due_email_digests()

    def test_not_flushed_before_window_closes(self):
        from apps.notifications.digest import queue_notification_email, flush_due_email_digests

        queue_notification_email(make_note(self.user))
        mail.outbox = []
        flush_due_email_digests()  # send_after is ~5 min out
        self.assertEqual(len(mail.outbox), 0)

    def test_single_pending_sends_single_email(self):
        from apps.notifications.digest import queue_notification_email
        from apps.notifications.models import EmailDigest

        queue_notification_email(make_note(self.user, title='New message from Alice Scholar'))
        mail.outbox = []
        self._flush_now()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Alice Scholar', mail.outbox[0].subject)
        self.assertFalse(EmailDigest.objects.filter(user=self.user).exists())
        self.assertFalse(Notification.objects.filter(user=self.user, email_pending=True).exists())

    def test_ten_messages_produce_one_summary_email(self):
        from apps.notifications.digest import queue_notification_email

        for i in range(10):
            queue_notification_email(make_note(self.user, title=f'New message from Scholar {i}'))
        mail.outbox = []
        self._flush_now()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('10', mail.outbox[0].body)

    def test_read_notifications_are_not_emailed(self):
        from apps.notifications.digest import queue_notification_email
        from apps.notifications.models import EmailDigest

        n1 = make_note(self.user)
        n2 = make_note(self.user)
        queue_notification_email(n1)
        queue_notification_email(n2)
        # Recipient read both in-app before the window closed.
        Notification.objects.filter(pk__in=[n1.pk, n2.pk]).update(is_read=True)

        mail.outbox = []
        self._flush_now()
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EmailDigest.objects.filter(user=self.user).exists())

    def test_only_unread_are_summarised(self):
        from apps.notifications.digest import queue_notification_email

        read = make_note(self.user, title='read one')
        make_note(self.user, title='unread A')  # queued below
        unread_b = make_note(self.user, title='unread B')
        for n in Notification.objects.filter(user=self.user):
            queue_notification_email(n)
        Notification.objects.filter(pk=read.pk).update(is_read=True)

        mail.outbox = []
        self._flush_now()
        self.assertEqual(len(mail.outbox), 1)
        # summary of 2 unread, not 3
        self.assertIn('2', mail.outbox[0].body)

    # --- sliding window cap ---------------------------------------------

    def test_window_slides_but_is_capped(self):
        from apps.notifications.digest import queue_notification_email
        from apps.notifications.models import EmailDigest

        queue_notification_email(make_note(self.user))
        digest = EmailDigest.objects.get(user=self.user)
        # Pretend the window opened ~14m50s ago (near the 15m cap) and the last
        # slide left send_after consistently inside the window.
        opened = timezone.now() - timedelta(seconds=890)
        EmailDigest.objects.filter(pk=digest.pk).update(
            window_started_at=opened, send_after=opened + timedelta(seconds=300),
        )

        # A fresh notification arrives now; a naive slide would push send_after to
        # now + 300 (~opened + 1190), but the cap must clamp it to opened + 900.
        queue_notification_email(make_note(self.user))
        digest.refresh_from_db()
        self.assertLessEqual(digest.send_after, opened + timedelta(seconds=900))
        # And it did move forward toward the cap (proving the slide happened).
        self.assertGreater(digest.send_after, opened + timedelta(seconds=300))
