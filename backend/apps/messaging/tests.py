"""
Regression tests for message persistence and history loading (UAT P1-1b).

Round-2 root cause: messages were persisted correctly, but the history
endpoint is paginated oldest-first and the frontend only read page 1, so any
thread longer than PAGE_SIZE hid all recent messages after a reload.  These
tests pin the API contract the frontend now depends on.

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test apps.messaging --verbosity=2
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import User
from .models import Conversation, Message


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


class MessageModerationOutcomeTests(TestCase):
    """MSG-04: clean messages deliver, contact details are HELD for review (not
    blocked), and genuinely blocked terms stop delivery."""

    def setUp(self):
        from apps.moderation.service import ModerationService
        from apps.moderation.models import ModerationTerm
        ModerationService.invalidate_cache()
        ModerationTerm.objects.create(
            term='murder', match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.CRITICAL, source='bulk_import_v1', is_active=True,
        )
        ModerationService.invalidate_cache()
        self.scholar = make_user('scholar-mod@example.com', role=User.Role.SCHOLAR)
        self.mentor = make_user('mentor-mod@example.com', role=User.Role.MENTOR)
        self.conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT, subject='Test'
        )
        self.conv.participants.set([self.scholar, self.mentor])
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.scholar)

    def tearDown(self):
        from apps.moderation.service import ModerationService
        ModerationService.invalidate_cache()

    def _send(self, body):
        return self.client_api.post(
            '/api/messaging/messages/', {'conversation': self.conv.pk, 'body': body},
        )

    def test_clean_message_delivers(self):
        resp = self._send('Hi, thanks for the great session today.')
        self.assertEqual(resp.status_code, 201, resp.content)
        msg = Message.objects.get(body__startswith='Hi, thanks')
        self.assertEqual(msg.status, Message.Status.DELIVERED)

    def test_bare_at_is_held_for_review(self):
        resp = self._send('reach me at jordan@example.com')
        self.assertEqual(resp.status_code, 202, resp.content)
        self.assertEqual(resp.data['moderation_status'], 'pending_review')
        msg = Message.objects.get(body__startswith='reach me')
        self.assertEqual(msg.status, Message.Status.FLAGGED)

    def test_phone_number_is_held_for_review(self):
        resp = self._send('call me on 07700 900123')
        self.assertEqual(resp.status_code, 202, resp.content)
        msg = Message.objects.get(body__startswith='call me')
        self.assertEqual(msg.status, Message.Status.FLAGGED)

    def test_blocked_term_stops_delivery(self):
        resp = self._send('I want to murder someone')
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.data['moderation_status'], 'blocked')
        msg = Message.objects.get(body__startswith='I want')
        self.assertEqual(msg.status, Message.Status.BLOCKED)

    def test_held_message_does_not_announce_moderator_review(self):
        """An automatic hold must NOT post a system message claiming a moderator
        reviewed and permanently blocked the message (MSG-04)."""
        self._send('reach me at jordan@example.com')
        system_msgs = Message.objects.filter(sender__email='arkwright@spt.org')
        for m in system_msgs:
            self.assertNotIn('permanently blocked', m.body.lower())
            self.assertNotIn('reviewed by a moderator', m.body.lower())


class HeldMessageVisibilityTests(TestCase):
    """P2-1(a): the sender of a held/blocked message must still see it in
    their own thread, with a safe, category-level reason. Other participants
    must never see held/blocked content, recipient privacy is the critical
    invariant here."""

    def setUp(self):
        from apps.moderation.service import ModerationService
        from apps.moderation.models import ModerationTerm
        ModerationService.invalidate_cache()
        ModerationTerm.objects.create(
            term='murder', match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.CRITICAL, source='bulk_import_v1', is_active=True,
        )
        ModerationService.invalidate_cache()
        self.scholar = make_user('scholar-held@example.com', role=User.Role.SCHOLAR)
        self.mentor = make_user('mentor-held@example.com', role=User.Role.MENTOR)
        self.conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT, subject='Test'
        )
        self.conv.participants.set([self.scholar, self.mentor])
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.scholar)

    def tearDown(self):
        from apps.moderation.service import ModerationService
        ModerationService.invalidate_cache()

    def test_sender_sees_own_flagged_message_with_status(self):
        resp = self.client_api.post(
            '/api/messaging/messages/',
            {'conversation': self.conv.pk, 'body': 'reach me @ mydomain'},
        )
        self.assertEqual(resp.status_code, 202, resp.content)
        listing = self.client_api.get(f'/api/messaging/messages/?conversation={self.conv.pk}')
        statuses = {m['id']: m['status'] for m in listing.data['results']}
        self.assertIn('flagged', statuses.values())

    def test_recipient_does_not_see_held_message(self):
        resp = self.client_api.post(
            '/api/messaging/messages/',
            {'conversation': self.conv.pk, 'body': 'reach me @ mydomain'},
        )
        self.assertEqual(resp.status_code, 202, resp.content)
        held_id = resp.data['message']['id']

        other_client = APIClient()
        other_client.force_authenticate(self.mentor)
        listing = other_client.get(f'/api/messaging/messages/?conversation={self.conv.pk}')
        ids = [m['id'] for m in listing.data['results']]
        self.assertNotIn(held_id, ids)

    def test_block_response_names_category_not_term(self):
        resp = self.client_api.post(
            '/api/messaging/messages/',
            {'conversation': self.conv.pk, 'body': 'I want to murder someone'},
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn('moderation_reason', resp.data)
        self.assertNotIn('murder', resp.data['detail'])
        self.assertNotIn('murder', resp.data['moderation_reason'])
        self.assertEqual(
            resp.data['moderation_reason'],
            'it contains wording that is not permitted on the platform',
        )
        self.assertIn('message', resp.data)
        self.assertEqual(resp.data['message']['status'], 'blocked')

    def test_flagged_response_includes_reason_and_serialised_message(self):
        resp = self.client_api.post(
            '/api/messaging/messages/',
            {'conversation': self.conv.pk, 'body': 'reach me @ mydomain'},
        )
        self.assertEqual(resp.status_code, 202, resp.content)
        self.assertEqual(
            resp.data['moderation_reason'],
            'it appears to contain contact details (such as an email address or phone number)',
        )
        self.assertIn('message', resp.data)
        self.assertEqual(resp.data['message']['status'], 'flagged')

    def test_url_fragment_reason_names_web_link(self):
        from apps.moderation.models import ModerationTerm
        from apps.moderation.service import ModerationService
        ModerationTerm.objects.create(
            term='www', match_type=ModerationTerm.MatchType.URL_FRAGMENT,
            severity=ModerationTerm.Severity.HIGH, source='bulk_import_v1', is_active=True,
        )
        ModerationService.invalidate_cache()

        resp = self.client_api.post(
            '/api/messaging/messages/',
            {'conversation': self.conv.pk, 'body': 'visit www.example.com for details'},
        )
        self.assertEqual(resp.status_code, 202, resp.content)
        self.assertEqual(resp.data['moderation_reason'], 'it contains a web link')


class MassMessageSendTests(TestCase):
    """MSG-06: mass sends are queued on the worker and return immediately."""

    def setUp(self):
        from .models import MassMessage
        self.admin = make_user('mm-admin@example.com', role=User.Role.ADMIN, is_staff=True)
        self.mm = MassMessage.objects.create(
            sender=self.admin, subject='Hello all', body='Welcome', recipient_roles=['scholar'],
        )
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.admin)

    def test_send_queues_in_background_and_returns_promptly(self):
        from unittest.mock import patch
        from .models import MassMessage
        with patch('apps.messaging.tasks.send_mass_message_task.delay') as delay:
            resp = self.client_api.post(f'/api/messaging/mass-messages/{self.mm.pk}/send/')
        self.assertEqual(resp.status_code, 202, resp.content)
        delay.assert_called_once_with(self.mm.pk)
        self.mm.refresh_from_db()
        self.assertEqual(self.mm.status, MassMessage.Status.SENDING)

    def test_double_send_is_rejected(self):
        from unittest.mock import patch
        with patch('apps.messaging.tasks.send_mass_message_task.delay'):
            self.client_api.post(f'/api/messaging/mass-messages/{self.mm.pk}/send/')
            resp = self.client_api.post(f'/api/messaging/mass-messages/{self.mm.pk}/send/')
        self.assertEqual(resp.status_code, 400)


class MassMessageBodySanitisedOnSaveTests(TestCase):
    """Task 24 hardening: MassMessageViewSet (REST API) writes body without
    going through the admin form's clean_body(), so the gate must also live
    on the model - sanitise_rich_text() must run on every save(), not just
    on the admin form path."""

    def test_script_in_body_is_stripped_when_created_via_the_orm(self):
        from .models import MassMessage
        admin = make_user('mm-orm-admin@example.com', role=User.Role.ADMIN, is_staff=True)
        mm = MassMessage.objects.create(
            sender=admin, subject='Hello', body='<p>Hi</p><script>alert(1)</script>',
        )
        mm.refresh_from_db()
        self.assertNotIn('<script', mm.body)
        self.assertNotIn('alert(1)', mm.body)
        self.assertIn('Hi', mm.body)

    def test_plain_text_body_is_unaffected_by_save(self):
        from .models import MassMessage
        admin = make_user('mm-orm-admin-plain@example.com', role=User.Role.ADMIN, is_staff=True)
        mm = MassMessage.objects.create(sender=admin, subject='Hello', body='Just plain text.')
        mm.refresh_from_db()
        self.assertEqual(mm.body, 'Just plain text.')


class MassMessageHtmlEmailTests(TestCase):
    """Task 24: mass message emails carry the (sanitised) HTML body as the
    primary content, with a plain-text fallback for clients that can't
    render HTML - not the raw markup as the plain body.

    Task 24 hardening: a body with no tags at all (the plain AdminPage
    textarea path) must be sent as a genuinely plain email - no
    html_message alternative - not wrapped as "HTML" with nothing to
    render. HTML_RE gates on tag presence so both cases are covered."""

    def setUp(self):
        from django.core import mail
        mail.outbox = []
        self.admin = make_user('mm-html-admin@example.com', role=User.Role.ADMIN, is_staff=True)
        self.recipient = make_user(
            'mm-html-recipient@example.com', role=User.Role.SCHOLAR, notification_email=True,
        )

    def _send(self, body):
        from .models import MassMessage
        from .tasks import send_mass_message_task
        mm = MassMessage.objects.create(
            sender=self.admin, subject='Announcement', body=body, recipient_roles=['scholar'],
        )
        send_mass_message_task(mm.pk)

    def test_rich_body_has_html_alternative_and_plain_text_fallback(self):
        from django.core import mail
        self._send('<p>Hello <b>everyone</b></p>')

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]

        # Plain body is markup-free.
        self.assertNotIn('<b>', sent.body)
        self.assertNotIn('<p>', sent.body)
        self.assertIn('Hello', sent.body)
        self.assertIn('everyone', sent.body)

        # HTML alternative carries the original markup.
        html_alternatives = [content for content, mimetype in sent.alternatives if mimetype == 'text/html']
        self.assertEqual(len(html_alternatives), 1)
        self.assertIn('<b>everyone</b>', html_alternatives[0])

    def test_plain_body_has_no_html_alternative_and_keeps_newlines(self):
        from django.core import mail
        plain_body = 'Hello everyone,\n\nSecond paragraph, no markup here.'
        self._send(plain_body)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]

        self.assertEqual(sent.body, plain_body)
        self.assertEqual(sent.alternatives, [])


class MessageHistoryTests(TestCase):
    """The history endpoint must return every delivered message in a thread."""

    def setUp(self):
        self.scholar = make_user('scholar-hist@example.com', role=User.Role.SCHOLAR)
        self.mentor = make_user('mentor-hist@example.com', role=User.Role.MENTOR)
        self.conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT, subject='Test'
        )
        self.conv.participants.set([self.scholar, self.mentor])
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.scholar)

    def test_rest_send_persists_message_as_delivered(self):
        resp = self.client_api.post(
            '/api/messaging/messages/',
            {'conversation': self.conv.pk, 'body': 'Hello mentor'},
        )
        self.assertEqual(resp.status_code, 201)
        msg = Message.objects.get(conversation=self.conv)
        self.assertEqual(msg.status, Message.Status.DELIVERED)
        self.assertEqual(msg.sender, self.scholar)

    def test_history_returns_message_after_send(self):
        self.client_api.post(
            '/api/messaging/messages/',
            {'conversation': self.conv.pk, 'body': 'Hello mentor'},
        )
        resp = self.client_api.get(f'/api/messaging/messages/?conversation={self.conv.pk}')
        self.assertEqual(resp.status_code, 200)
        bodies = [m['body'] for m in resp.data['results']]
        self.assertIn('Hello mentor', bodies)

    def test_history_count_covers_full_thread_and_pages_are_complete(self):
        """A thread longer than one page must expose every message via `next` links.

        This is the P1-1b regression: page 1 alone only holds the oldest
        PAGE_SIZE messages, so the API must report the full count and a
        traversable `next` link chain that yields the most recent message.
        """
        for i in range(30):
            Message.objects.create(
                conversation=self.conv, sender=self.scholar,
                body=f'message {i}', status=Message.Status.DELIVERED,
            )
        resp = self.client_api.get(f'/api/messaging/messages/?conversation={self.conv.pk}')
        self.assertEqual(resp.data['count'], 30)
        self.assertIsNotNone(resp.data['next'])

        # Walk every page the way the frontend now does.
        bodies, page = [], 1
        while True:
            resp = self.client_api.get(
                f'/api/messaging/messages/?conversation={self.conv.pk}&page={page}'
            )
            bodies += [m['body'] for m in resp.data['results']]
            if not resp.data['next']:
                break
            page += 1
        self.assertEqual(len(bodies), 30)
        self.assertEqual(bodies[-1], 'message 29')

    def test_history_excludes_blocked_and_flagged_for_non_staff(self):
        """The RECIPIENT of held/blocked content must never see it. The SENDER,
        however, must still see their own held/blocked messages in their own
        thread (P2-1a). Recipient privacy is the invariant that matters."""
        Message.objects.create(
            conversation=self.conv, sender=self.scholar,
            body='clean', status=Message.Status.DELIVERED,
        )
        Message.objects.create(
            conversation=self.conv, sender=self.scholar,
            body='naughty', status=Message.Status.BLOCKED,
        )
        Message.objects.create(
            conversation=self.conv, sender=self.scholar,
            body='suspicious', status=Message.Status.FLAGGED,
        )

        # Sender (self.scholar is authenticated on self.client_api) sees all three.
        resp = self.client_api.get(f'/api/messaging/messages/?conversation={self.conv.pk}')
        bodies = {m['body'] for m in resp.data['results']}
        self.assertEqual(bodies, {'clean', 'naughty', 'suspicious'})

        # The other participant (recipient) only ever sees delivered content.
        other_client = APIClient()
        other_client.force_authenticate(self.mentor)
        resp = other_client.get(f'/api/messaging/messages/?conversation={self.conv.pk}')
        bodies = [m['body'] for m in resp.data['results']]
        self.assertEqual(bodies, ['clean'])

    def test_scholar_cannot_open_conversation_with_unmatched_mentor(self):
        """MSG-05: never-matched pairs must not be able to start a direct
        conversation, and no conversation may be created by the attempt."""
        stranger = make_user('stranger-mentor@example.com', role=User.Role.MENTOR)
        before = Conversation.objects.count()
        resp = self.client_api.post(
            '/api/messaging/conversations/',
            {'conversation_type': 'direct', 'participants': [stranger.pk]},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Conversation.objects.count(), before)

    def test_scholar_can_open_conversation_with_actively_matched_mentor(self):
        from apps.users.models import MentoringMatch
        MentoringMatch.objects.create(scholar=self.scholar, mentor=self.mentor, is_active=True)
        resp = self.client_api.post(
            '/api/messaging/conversations/',
            {'conversation_type': 'direct', 'participants': [self.mentor.pk]},
        )
        self.assertEqual(resp.status_code, 201)

    def test_non_participant_sees_no_messages(self):
        Message.objects.create(
            conversation=self.conv, sender=self.scholar,
            body='private', status=Message.Status.DELIVERED,
        )
        outsider = make_user('outsider-hist@example.com', role=User.Role.SCHOLAR)
        client = APIClient()
        client.force_authenticate(outsider)
        resp = client.get(f'/api/messaging/messages/?conversation={self.conv.pk}')
        self.assertEqual(resp.data['count'], 0)


class AbuseReportContentTests(TestCase):
    """P2-6: every abuse report must carry the reported content for admins."""

    def setUp(self):
        self.scholar = make_user('scholar-rep@example.com', role=User.Role.SCHOLAR)
        self.mentor = make_user('mentor-rep@example.com', role=User.Role.MENTOR)
        self.conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT, subject='Test'
        )
        self.conv.participants.set([self.scholar, self.mentor])
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.scholar)

    def test_message_report_snapshots_message_body(self):
        from .models import AbuseReport
        msg = Message.objects.create(
            conversation=self.conv, sender=self.mentor,
            body='something concerning', status=Message.Status.DELIVERED,
        )
        resp = self.client_api.post('/api/messaging/abuse-reports/', {
            'message': msg.pk,
            'reported_user': self.mentor.pk,
            'description': 'worried about this',
        })
        self.assertEqual(resp.status_code, 201, resp.content)
        report = AbuseReport.objects.get()
        self.assertEqual(report.reported_content, 'something concerning')
        self.assertEqual(report.message, msg)
        self.assertEqual(report.reported_user, self.mentor)

    def test_forum_style_report_keeps_supplied_content(self):
        from .models import AbuseReport
        resp = self.client_api.post('/api/messaging/abuse-reports/', {
            'reported_user': self.mentor.pk,
            'description': 'Reported forum post #5',
            'reported_content': 'call me on 07700900000',
        })
        self.assertEqual(resp.status_code, 201, resp.content)
        report = AbuseReport.objects.get()
        self.assertEqual(report.reported_content, 'call me on 07700900000')

    def test_admin_displays_snapshot_even_after_message_deleted(self):
        from .models import AbuseReport
        from .admin import AbuseReportAdmin
        from django.contrib import admin as dj_admin
        msg = Message.objects.create(
            conversation=self.conv, sender=self.mentor,
            body='to be deleted', status=Message.Status.DELIVERED,
        )
        self.client_api.post('/api/messaging/abuse-reports/', {
            'message': msg.pk, 'description': 'concern',
        })
        msg.delete()
        report = AbuseReport.objects.get()
        admin_obj = AbuseReportAdmin(AbuseReport, dj_admin.site)
        self.assertIn('to be deleted', str(admin_obj.reported_message_body(report)))
        self.assertIn('to be deleted', admin_obj.reported_message_preview(report))


class MessageWhitespaceTests(TestCase):
    """Internal whitespace and newlines must survive storage and serialization (P1-2)."""

    def setUp(self):
        self.scholar = make_user('scholar-ws@example.com', role=User.Role.SCHOLAR)
        self.mentor = make_user('mentor-ws@example.com', role=User.Role.MENTOR)
        self.conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT, subject='Test'
        )
        self.conv.participants.set([self.scholar, self.mentor])
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.scholar)

    def test_internal_whitespace_and_newlines_preserved(self):
        body = 'def f():\n    return  1\n\n\ttabbed'
        resp = self.client_api.post(
            '/api/messaging/messages/', {'conversation': self.conv.pk, 'body': body},
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        msg = Message.objects.get(id=resp.data['id'])
        self.assertEqual(msg.body, body)
        list_resp = self.client_api.get(f'/api/messaging/messages/?conversation={self.conv.pk}')
        bodies = [m['body'] for m in list_resp.data['results']]
        self.assertIn(body, bodies)


class AdminStartConversationTests(TestCase):
    """Admins can start a brand-new direct message to any user from the Django
    admin, sent as the Arkwright support account.

    Fills the reported gap: admins previously had no way to initiate a
    conversation — they could only reply to threads a user had already started.
    """

    def setUp(self):
        self.admin = make_user(
            'boss@spt.org', role=User.Role.ADMIN, is_staff=True, is_superuser=True,
        )
        self.mentor = make_user('mentee_mentor@example.com', role=User.Role.MENTOR)
        self.client.force_login(self.admin)
        self.url = reverse('admin:messaging_conversation_start')

    def test_get_renders_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="recipient"')
        self.assertContains(resp, 'name="body"')

    def test_post_creates_direct_conversation_with_delivered_message(self):
        resp = self.client.post(self.url, {
            'recipient': self.mentor.pk,
            'subject': 'Quick question',
            'body': 'Hello, could you please update your availability?',
        })
        self.assertEqual(resp.status_code, 302)

        arkwright = User.objects.get(email='arkwright@spt.org')
        conv = Conversation.objects.get(
            conversation_type=Conversation.ConversationType.DIRECT,
            subject='Quick question',
        )
        self.assertSetEqual(
            set(conv.participants.values_list('pk', flat=True)),
            {arkwright.pk, self.mentor.pk},
        )
        msg = conv.messages.get()
        self.assertEqual(msg.sender, arkwright)
        self.assertEqual(msg.status, Message.Status.DELIVERED)
        self.assertEqual(msg.body, 'Hello, could you please update your availability?')

    def test_post_notifies_recipient(self):
        from apps.notifications.models import Notification
        self.client.post(self.url, {'recipient': self.mentor.pk, 'body': 'Hi there'})
        self.assertTrue(
            Notification.objects.filter(
                user=self.mentor, notification_type=Notification.Type.MESSAGE,
            ).exists()
        )

    def test_reuses_existing_arkwright_thread(self):
        """A second message to the same person appends to the existing thread
        rather than spawning a duplicate support conversation."""
        self.client.post(self.url, {'recipient': self.mentor.pk, 'body': 'First'})
        self.client.post(self.url, {'recipient': self.mentor.pk, 'body': 'Second'})
        arkwright = User.objects.get(email='arkwright@spt.org')
        convs = Conversation.objects.filter(
            participants=arkwright, conversation_type=Conversation.ConversationType.DIRECT,
        ).filter(participants=self.mentor).distinct()
        self.assertEqual(convs.count(), 1)
        self.assertEqual(convs.first().messages.count(), 2)

    def test_empty_body_is_rejected(self):
        resp = self.client.post(self.url, {'recipient': self.mentor.pk, 'body': '   '})
        self.assertEqual(resp.status_code, 200)  # re-rendered with error
        self.assertEqual(Message.objects.count(), 0)

    def test_non_staff_cannot_access(self):
        self.client.force_login(self.mentor)  # a plain mentor, not staff
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, (302, 403))  # admin_view bounces non-staff


class NoContactReminderEmailTests(TestCase):
    """P2-3c: no-contact reminder emails must name the mentoring partner (full
    name + role) and link to the platform, not just say 'mentoring partner'."""

    def setUp(self):
        from django.core import mail
        from apps.users.models import MentoringMatch
        mail.outbox = []
        self.scholar = make_user(
            'noreply-scholar@example.com', role=User.Role.SCHOLAR,
            first_name='Sam', last_name='Scholar', notification_email=True,
        )
        self.mentor = make_user(
            'noreply-mentor@example.com', role=User.Role.MENTOR,
            first_name='Mo', last_name='Mentor', notification_email=True,
        )
        # No messages have ever been exchanged, so the pair is stale
        # regardless of settings.NO_CONTACT_REMINDER_DAYS.
        self.match = MentoringMatch.objects.create(scholar=self.scholar, mentor=self.mentor)

    def test_reminder_emails_name_partner_and_link_platform(self):
        from django.conf import settings
        from django.core import mail
        from .tasks import send_no_contact_reminders
        send_no_contact_reminders()

        self.assertEqual(len(mail.outbox), 2)
        by_recipient = {m.to[0]: m for m in mail.outbox}

        scholar_email = by_recipient[self.scholar.email]
        self.assertIn('Mo Mentor', scholar_email.body)
        self.assertIn('mentor', scholar_email.body)
        self.assertIn(f'{settings.FRONTEND_URL}/messages', scholar_email.body)

        mentor_email = by_recipient[self.mentor.email]
        self.assertIn('Sam Scholar', mentor_email.body)
        self.assertIn('scholar', mentor_email.body)
        self.assertIn(f'{settings.FRONTEND_URL}/messages', mentor_email.body)


class MessageEditTests(TestCase):
    """Task 13 (P2-4): senders can edit their own messages, edits are always
    re-moderated, and the previously unmoderated PATCH/PUT/DELETE holes are
    closed. HistoricalRecords on Message is the audit trail for edits."""

    def setUp(self):
        from apps.moderation.service import ModerationService
        from apps.moderation.models import ModerationTerm
        ModerationService.invalidate_cache()
        ModerationTerm.objects.create(
            term='murder', match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.CRITICAL, source='bulk_import_v1', is_active=True,
        )
        ModerationService.invalidate_cache()
        self.scholar = make_user('scholar-edit@example.com', role=User.Role.SCHOLAR)
        self.mentor = make_user('mentor-edit@example.com', role=User.Role.MENTOR)
        self.conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT, subject='Edit tests'
        )
        self.conv.participants.set([self.scholar, self.mentor])
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.scholar)

    def tearDown(self):
        from apps.moderation.service import ModerationService
        ModerationService.invalidate_cache()

    def _send(self, body):
        return self.client_api.post(
            '/api/messaging/messages/', {'conversation': self.conv.pk, 'body': body},
        )

    def _patch(self, message_id, body, client=None):
        return (client or self.client_api).patch(
            f'/api/messaging/messages/{message_id}/', {'body': body},
        )

    def _mentor_message_notifications(self):
        from apps.notifications.models import Notification
        return Notification.objects.filter(
            user=self.mentor, notification_type=Notification.Type.MESSAGE,
        )

    def test_sender_edits_own_delivered_message_within_window(self):
        resp = self._send('Original clean message, see you soon.')
        self.assertEqual(resp.status_code, 201, resp.content)
        msg = Message.objects.get(pk=resp.data['id'])
        history_before = msg.history.count()

        edit = self._patch(msg.pk, 'Actually let us meet on Friday instead.')
        self.assertEqual(edit.status_code, 200, edit.content)
        self.assertEqual(edit.data['body'], 'Actually let us meet on Friday instead.')
        self.assertIsNotNone(edit.data['edited_at'])

        msg.refresh_from_db()
        self.assertEqual(msg.body, 'Actually let us meet on Friday instead.')
        self.assertEqual(msg.status, Message.Status.DELIVERED)
        self.assertIsNotNone(msg.edited_at)
        # HistoricalRecords is the audit trail - history must grow on edit.
        self.assertGreater(msg.history.count(), history_before)

    def test_edit_to_blocked_term_returns_blocked_envelope(self):
        resp = self._send('Original clean message.')
        self.assertEqual(resp.status_code, 201, resp.content)
        msg_id = resp.data['id']

        edit = self._patch(msg_id, 'I want to murder someone')
        self.assertEqual(edit.status_code, 400, edit.content)
        self.assertEqual(edit.data['moderation_status'], 'blocked')
        self.assertIn('moderation_reason', edit.data)
        msg = Message.objects.get(pk=msg_id)
        self.assertEqual(msg.status, Message.Status.BLOCKED)
        self.assertIsNotNone(msg.edited_at)

        # Own blocked message stays editable - a clean re-edit releases it.
        notifications_before = self._mentor_message_notifications().count()
        reedit = self._patch(msg_id, 'Sorry about that, back to the clean version.')
        self.assertEqual(reedit.status_code, 200, reedit.content)
        msg.refresh_from_db()
        self.assertEqual(msg.status, Message.Status.DELIVERED)
        # Releasing a blocked message notifies the recipient (once).
        self.assertEqual(
            self._mentor_message_notifications().count(), notifications_before + 1
        )

    def test_flagged_message_edited_to_clean_is_delivered_and_notifies_once(self):
        resp = self._send('reach me at jordan@example.com')
        self.assertEqual(resp.status_code, 202, resp.content)
        msg_id = resp.data['message']['id']
        # Held message never notified the recipient.
        self.assertEqual(self._mentor_message_notifications().count(), 0)

        edit = self._patch(msg_id, 'Sorry, I will share notes in our next session.')
        self.assertEqual(edit.status_code, 200, edit.content)
        msg = Message.objects.get(pk=msg_id)
        self.assertEqual(msg.status, Message.Status.DELIVERED)
        # The release must notify the recipient exactly once.
        self.assertEqual(self._mentor_message_notifications().count(), 1)

        # Recipient can now see the released message.
        mentor_client = APIClient()
        mentor_client.force_authenticate(self.mentor)
        listing = mentor_client.get(f'/api/messaging/messages/?conversation={self.conv.pk}')
        ids = [m['id'] for m in listing.data['results']]
        self.assertIn(msg_id, ids)

    def test_admin_approval_of_edited_flagged_message_notifies_recipients(self):
        """Task 6 regression guard: releasing an EDITED flagged message via
        ModerationService.approve() must still notify recipients - the edit
        suppression only applies within the edit request itself."""
        from apps.moderation.service import ModerationService
        resp = self._send('reach me at jordan@example.com')
        self.assertEqual(resp.status_code, 202, resp.content)
        msg_id = resp.data['message']['id']

        # Edit to a body that is still held (phone number).
        edit = self._patch(msg_id, 'call me on 07700 900123')
        self.assertEqual(edit.status_code, 202, edit.content)
        self.assertEqual(self._mentor_message_notifications().count(), 0)

        admin = make_user('approver-edit@example.com', role=User.Role.ADMIN, is_staff=True)
        msg = Message.objects.get(pk=msg_id)
        self.assertIsNotNone(msg.edited_at)
        ModerationService.approve(msg, admin)
        msg.refresh_from_db()
        self.assertEqual(msg.status, Message.Status.DELIVERED)
        self.assertEqual(self._mentor_message_notifications().count(), 1)

    def test_held_message_editable_after_window(self):
        resp = self._send('reach me at jordan@example.com')
        self.assertEqual(resp.status_code, 202, resp.content)
        msg_id = resp.data['message']['id']
        from django.utils import timezone
        from datetime import timedelta
        Message.objects.filter(pk=msg_id).update(
            sent_at=timezone.now() - timedelta(hours=2)
        )
        edit = self._patch(msg_id, 'A clean replacement body.')
        self.assertEqual(edit.status_code, 200, edit.content)
        msg = Message.objects.get(pk=msg_id)
        self.assertEqual(msg.status, Message.Status.DELIVERED)

    def test_normal_send_still_notifies_recipients(self):
        resp = self._send('A perfectly normal clean message.')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self._mentor_message_notifications().count(), 1)

    def test_edit_of_delivered_message_does_not_duplicate_notifications(self):
        resp = self._send('A perfectly normal clean message.')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self._mentor_message_notifications().count(), 1)

        edit = self._patch(resp.data['id'], 'A clean edit of the same message.')
        self.assertEqual(edit.status_code, 200, edit.content)
        self.assertEqual(self._mentor_message_notifications().count(), 1)

    def test_cannot_edit_another_users_message(self):
        msg = Message.objects.create(
            conversation=self.conv, sender=self.mentor,
            body='Mentor message.', status=Message.Status.DELIVERED,
        )
        edit = self._patch(msg.pk, 'Hijacked body')
        self.assertEqual(edit.status_code, 403, edit.content)
        self.assertEqual(edit.data['detail'], 'You can only edit your own messages.')
        msg.refresh_from_db()
        self.assertEqual(msg.body, 'Mentor message.')

    def test_non_participant_cannot_edit(self):
        outsider = make_user('outsider-edit@example.com', role=User.Role.SCHOLAR)
        msg = Message.objects.create(
            conversation=self.conv, sender=self.scholar,
            body='Private message.', status=Message.Status.DELIVERED,
        )
        outsider_client = APIClient()
        outsider_client.force_authenticate(outsider)
        edit = self._patch(msg.pk, 'Hijacked body', client=outsider_client)
        self.assertEqual(edit.status_code, 404, edit.content)

    def test_delivered_message_not_editable_after_window(self):
        resp = self._send('Original clean message.')
        self.assertEqual(resp.status_code, 201, resp.content)
        msg_id = resp.data['id']
        from django.utils import timezone
        from datetime import timedelta
        Message.objects.filter(pk=msg_id).update(
            sent_at=timezone.now() - timedelta(minutes=16)
        )
        edit = self._patch(msg_id, 'Too late to change this.')
        self.assertEqual(edit.status_code, 403, edit.content)
        self.assertEqual(
            edit.data['detail'],
            'Messages can only be edited within 15 minutes of sending.',
        )

    def test_mass_message_not_editable(self):
        mass_conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.MASS_MESSAGE, subject='Broadcast'
        )
        mass_conv.participants.set([self.scholar, self.mentor])
        msg = Message.objects.create(
            conversation=mass_conv, sender=self.scholar,
            body='Broadcast body.', status=Message.Status.DELIVERED,
        )
        edit = self._patch(msg.pk, 'Edited broadcast')
        self.assertEqual(edit.status_code, 403, edit.content)
        self.assertEqual(edit.data['detail'], 'Broadcast messages cannot be edited.')

    def test_deleted_message_not_editable(self):
        # For a non-staff sender the visibility queryset (Task 5) hides
        # soft-deleted messages entirely, so the edit 404s.
        msg = Message.objects.create(
            conversation=self.conv, sender=self.scholar,
            body='Soft-deleted message.', status=Message.Status.DELETED,
        )
        edit = self._patch(msg.pk, 'Resurrected body')
        self.assertEqual(edit.status_code, 404, edit.content)
        msg.refresh_from_db()
        self.assertEqual(msg.body, 'Soft-deleted message.')

        # A staff sender CAN load a deleted message, but the status guard
        # still refuses the edit.
        admin = make_user('admin-edit@example.com', role=User.Role.ADMIN, is_staff=True)
        self.conv.participants.add(admin)
        admin_msg = Message.objects.create(
            conversation=self.conv, sender=admin,
            body='Deleted admin message.', status=Message.Status.DELETED,
        )
        admin_client = APIClient()
        admin_client.force_authenticate(admin)
        edit = self._patch(admin_msg.pk, 'Resurrected body', client=admin_client)
        self.assertEqual(edit.status_code, 403, edit.content)
        self.assertEqual(edit.data['detail'], 'This message cannot be edited.')

    def test_empty_body_rejected(self):
        resp = self._send('Original clean message.')
        self.assertEqual(resp.status_code, 201, resp.content)
        edit = self._patch(resp.data['id'], '   ')
        self.assertEqual(edit.status_code, 400, edit.content)
        self.assertEqual(edit.data['detail'], 'Message body cannot be empty.')

    def test_put_and_delete_are_rejected(self):
        resp = self._send('Original clean message.')
        self.assertEqual(resp.status_code, 201, resp.content)
        msg_id = resp.data['id']
        put = self.client_api.put(
            f'/api/messaging/messages/{msg_id}/',
            {'conversation': self.conv.pk, 'body': 'Replaced'},
        )
        self.assertEqual(put.status_code, 405, put.content)
        delete = self.client_api.delete(f'/api/messaging/messages/{msg_id}/')
        self.assertEqual(delete.status_code, 405, delete.content)
        msg = Message.objects.get(pk=msg_id)
        self.assertEqual(msg.body, 'Original clean message.')
