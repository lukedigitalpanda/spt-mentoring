"""
Tests for per-notification email dispatch (sprint item N-1).

Root cause fixed here: browser push was dispatched by a post_save signal on
Notification, but there was no equivalent email path, so mentors with email
notifications enabled never received an email for a new message.

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test apps.notifications --verbosity=2
"""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone

from apps.users.models import User
from apps.notifications.models import Notification


def flush_email_digests_now():
    """Force any open debounce window due and flush it (N-3)."""
    from apps.notifications.models import EmailDigest
    from apps.notifications.digest import flush_due_email_digests
    EmailDigest.objects.update(send_after=timezone.now() - timedelta(seconds=1))
    flush_due_email_digests()


def make_user(email='mentor@example.com', **kwargs):
    defaults = dict(
        username=email.split('@')[0],
        email=email,
        first_name=email.split('@')[0].title(),
        last_name='Test',
        role=User.Role.MENTOR,
        is_active=True,
        is_verified=True,
        notification_email=True,
    )
    defaults.update(kwargs)
    return User.objects.create(**defaults)


@override_settings(FRONTEND_URL='https://mentoring.example.test')
class SendNotificationEmailTests(TestCase):
    """N-1: send_notification_email() emails the recipient for emailable types."""

    def test_sends_email_for_message_notification_when_enabled(self):
        from apps.notifications.emails import send_notification_email

        user = make_user(notification_email=True)
        notification = Notification.objects.create(
            user=user,
            notification_type=Notification.Type.MESSAGE,
            title='New message from Alice Scholar',
            body='Hi, are we still on for Tuesday?',
            link='/messages',
        )

        mail.outbox = []
        send_notification_email(notification)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['mentor@example.com'])
        self.assertIn('New message from Alice Scholar', sent.subject)
        # Deep link is a full URL the recipient can click from their inbox.
        self.assertIn('https://mentoring.example.test/messages', sent.body)

    def test_no_email_when_recipient_opted_out(self):
        from apps.notifications.emails import send_notification_email

        user = make_user(notification_email=False)
        notification = Notification.objects.create(
            user=user,
            notification_type=Notification.Type.MESSAGE,
            title='New message',
            body='hello',
            link='/messages',
        )

        mail.outbox = []
        result = send_notification_email(notification)

        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_no_email_for_non_emailable_type(self):
        """SYSTEM/session/news notifications must not start emailing (they never did)."""
        from apps.notifications.emails import send_notification_email

        user = make_user(notification_email=True)
        notification = Notification.objects.create(
            user=user,
            notification_type=Notification.Type.SYSTEM,
            title='Something happened',
            body='details',
            link='/',
        )

        mail.outbox = []
        result = send_notification_email(notification)

        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_no_email_when_user_has_no_address(self):
        from apps.notifications.emails import send_notification_email

        user = make_user(email='blank@example.com', notification_email=True)
        User.objects.filter(pk=user.pk).update(email='')
        user.refresh_from_db()
        notification = Notification.objects.create(
            user=user,
            notification_type=Notification.Type.MESSAGE,
            title='New message',
            body='hello',
            link='/messages',
        )

        mail.outbox = []
        result = send_notification_email(notification)

        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_failure_is_logged_not_swallowed(self):
        """N-1 acceptance: failures logged with recipient + type, never silent."""
        from unittest.mock import patch
        from apps.notifications import emails as emails_module

        user = make_user(notification_email=True)
        notification = Notification.objects.create(
            user=user,
            notification_type=Notification.Type.MESSAGE,
            title='New message',
            body='hello',
            link='/messages',
        )

        with patch.object(emails_module, 'send_mail', side_effect=RuntimeError('SMTP down')):
            with self.assertLogs('apps.notifications.emails', level='ERROR') as cm:
                result = emails_module.send_notification_email(notification)

        self.assertFalse(result)
        log_output = '\n'.join(cm.output)
        self.assertIn('mentor@example.com', log_output)
        self.assertIn(Notification.Type.MESSAGE, log_output)


@override_settings(
    FRONTEND_URL='https://mentoring.example.test',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class DeliveredMessageEmailTests(TestCase):
    """N-1 end-to-end: a delivered message emails the recipient (once)."""

    def _make_direct_message(self, sender, recipient, body='hello', conv_type=None):
        from apps.messaging.models import Conversation, Message
        conv = Conversation.objects.create(
            conversation_type=conv_type or Conversation.ConversationType.DIRECT,
            subject='Test',
        )
        conv.participants.set([sender, recipient])
        return Message.objects.create(
            conversation=conv, sender=sender, body=body,
            status=Message.Status.DELIVERED,
        )

    def test_delivered_message_emails_recipient(self):
        scholar = make_user('scholar@example.com', role=User.Role.SCHOLAR, notification_email=False)
        mentor = make_user('mentor@example.com', notification_email=True)

        mail.outbox = []
        self._make_direct_message(scholar, mentor, body='are we on for tuesday?')
        # Debounced: nothing sent until the window flushes.
        self.assertEqual(len(mail.outbox), 0)

        flush_email_digests_now()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['mentor@example.com'])

    def test_delivered_message_no_email_when_recipient_opted_out(self):
        scholar = make_user('scholar@example.com', role=User.Role.SCHOLAR, notification_email=False)
        mentor = make_user('mentor@example.com', notification_email=False)

        mail.outbox = []
        self._make_direct_message(scholar, mentor)
        flush_email_digests_now()

        self.assertEqual(len(mail.outbox), 0)

    def test_held_message_does_not_email_until_delivered(self):
        """A message held for moderation must not email; approval (→ delivered) does."""
        from apps.messaging.models import Conversation, Message
        scholar = make_user('scholar@example.com', role=User.Role.SCHOLAR, notification_email=False)
        mentor = make_user('mentor@example.com', notification_email=True)
        conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT, subject='Test',
        )
        conv.participants.set([scholar, mentor])

        mail.outbox = []
        message = Message.objects.create(
            conversation=conv, sender=scholar, body='call me on 07... ',
            status=Message.Status.FLAGGED,
        )
        self.assertEqual(len(mail.outbox), 0)

        # Admin approves -> delivered -> queued -> flush -> email fires.
        message.status = Message.Status.DELIVERED
        message.save(update_fields=['status'])
        flush_email_digests_now()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['mentor@example.com'])

    def test_mass_message_conversation_does_not_double_email(self):
        """Mass broadcasts send their own tailored email; the delivered-message
        signal must not also emit a generic one."""
        from apps.messaging.models import Conversation
        sender = make_user('arkwright@example.com', role=User.Role.ADMIN, notification_email=False)
        recipient = make_user('mentor@example.com', notification_email=True)

        mail.outbox = []
        self._make_direct_message(
            sender, recipient,
            conv_type=Conversation.ConversationType.MASS_MESSAGE,
        )
        flush_email_digests_now()

        self.assertEqual(len(mail.outbox), 0)
