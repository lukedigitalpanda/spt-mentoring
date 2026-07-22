"""
Task 6 (P2-1 backend part b): approving a held message must notify the
sender and deliver live over WebSocket, and the admin bulk `mark_delivered`
action must route through ModerationService.approve() so it gets the same
audit trail, notifications and broadcast as the single-message approve path.

Run with:
    docker compose exec -T backend python manage.py test apps.moderation apps.messaging -v 1
"""
from django.contrib import admin as dj_admin
from django.test import TestCase, RequestFactory

from apps.users.models import User
from apps.messaging.models import Conversation, Message
from apps.messaging.admin import MessageAdmin
from apps.moderation.models import ModerationLog
from apps.moderation.service import ModerationService
from apps.notifications.models import Notification


def make_user(email, role=User.Role.SCHOLAR, **kwargs):
    defaults = dict(
        username=email.split('@')[0],
        email=email,
        first_name=email.split('@')[0].title(),
        last_name='Test',
        role=role,
        is_active=True,
        is_verified=True,
        notification_email=False,
    )
    defaults.update(kwargs)
    return User.objects.create(**defaults)


class ApproveReleaseTests(TestCase):
    """ModerationService.approve() must deliver the message, notify the
    sender it was approved, and (unchanged) let the existing post_save
    signal notify the recipient."""

    def setUp(self):
        self.sender = make_user('scholar-release@example.com', role=User.Role.SCHOLAR)
        self.recipient = make_user('mentor-release@example.com', role=User.Role.MENTOR)
        self.admin = make_user(
            'admin-release@spt.org', role=User.Role.ADMIN, is_staff=True, is_superuser=True,
        )
        self.conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT, subject='Test',
        )
        self.conv.participants.set([self.sender, self.recipient])
        self.message = Message.objects.create(
            conversation=self.conv,
            sender=self.sender,
            body='held for review',
            status=Message.Status.FLAGGED,
        )

    def test_approve_sets_delivered_and_notifies_sender(self):
        ModerationService.approve(self.message, self.admin)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, Message.Status.DELIVERED)
        self.assertTrue(
            Notification.objects.filter(
                user=self.sender, title__icontains='approved',
            ).exists()
        )

    def test_approve_sender_notification_copy(self):
        ModerationService.approve(self.message, self.admin)
        notification = Notification.objects.get(
            user=self.sender, title__icontains='approved',
        )
        self.assertEqual(notification.title, 'Your message has been approved')
        self.assertEqual(
            notification.body, 'Your message has been reviewed and delivered.',
        )
        self.assertEqual(notification.link, '/messages')

    def test_approve_notifies_recipient(self):
        ModerationService.approve(self.message, self.admin)
        self.assertTrue(Notification.objects.filter(user=self.recipient).exists())

    def test_approve_creates_moderation_log(self):
        ModerationService.approve(self.message, self.admin)
        self.assertTrue(
            ModerationLog.objects.filter(
                message=self.message,
                action=ModerationLog.Action.APPROVED,
                actioned_by=self.admin,
            ).exists()
        )

    def test_approve_sets_audit_fields(self):
        ModerationService.approve(self.message, self.admin)
        self.message.refresh_from_db()
        self.assertEqual(self.message.moderated_by, self.admin)
        self.assertIsNotNone(self.message.moderated_at)

    def test_approve_broadcasts_without_error_when_channel_layer_missing(self):
        """The channel layer may be unavailable in some environments; approve()
        must not blow up in that case (it should no-op the broadcast)."""
        from unittest.mock import patch
        with patch('apps.moderation.service.get_channel_layer', return_value=None, create=True):
            ModerationService.approve(self.message, self.admin)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, Message.Status.DELIVERED)


class AdminMarkDeliveredTests(TestCase):
    """The bulk `mark_delivered` admin action must route through
    ModerationService.approve() rather than a bare queryset.update(), so the
    audit trail, notifications and broadcast all fire."""

    def setUp(self):
        self.sender = make_user('scholar-bulk@example.com', role=User.Role.SCHOLAR)
        self.recipient = make_user('mentor-bulk@example.com', role=User.Role.MENTOR)
        self.admin = make_user(
            'admin-bulk@spt.org', role=User.Role.ADMIN, is_staff=True, is_superuser=True,
        )
        self.conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT, subject='Test',
        )
        self.conv.participants.set([self.sender, self.recipient])
        self.message = Message.objects.create(
            conversation=self.conv,
            sender=self.sender,
            body='held for review',
            status=Message.Status.FLAGGED,
        )
        self.factory = RequestFactory()
        self.model_admin = MessageAdmin(Message, dj_admin.site)

    def _request(self):
        request = self.factory.post('/admin/messaging/message/')
        request.user = self.admin
        # message_user() needs session/messages middleware support.
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()
        request._messages = FallbackStorage(request)
        return request

    def test_admin_mark_delivered_routes_through_approve(self):
        request = self._request()
        queryset = Message.objects.filter(pk=self.message.pk)
        self.model_admin.mark_delivered(request, queryset)

        self.message.refresh_from_db()
        self.assertEqual(self.message.status, Message.Status.DELIVERED)
        self.assertEqual(self.message.moderated_by, self.admin)
        self.assertTrue(
            ModerationLog.objects.filter(
                message=self.message,
                action=ModerationLog.Action.APPROVED,
                actioned_by=self.admin,
            ).exists()
        )

    def test_admin_mark_delivered_notifies_sender_and_recipient(self):
        request = self._request()
        queryset = Message.objects.filter(pk=self.message.pk)
        self.model_admin.mark_delivered(request, queryset)

        self.assertTrue(
            Notification.objects.filter(
                user=self.sender, title__icontains='approved',
            ).exists()
        )
        self.assertTrue(Notification.objects.filter(user=self.recipient).exists())
