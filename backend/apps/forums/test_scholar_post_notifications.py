"""
Tests for sprint item N-2: notify a scholar's matched mentor(s) when the
scholar posts in a forum they can see.

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test apps.forums --verbosity=2
"""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import User, MentoringMatch
from apps.notifications.models import Notification
from apps.moderation.service import ModerationService
from .models import Forum, Thread, Post


def flush_email_digests_now():
    """Force any open debounce window due and flush it (N-3)."""
    from apps.notifications.models import EmailDigest
    from apps.notifications.digest import flush_due_email_digests
    EmailDigest.objects.update(send_after=timezone.now() - timedelta(seconds=1))
    flush_due_email_digests()


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


def make_match(scholar, mentor):
    return MentoringMatch.objects.create(scholar=scholar, mentor=mentor, is_active=True)


def make_thread(forum, author):
    return Thread.objects.create(forum=forum, title='Study plans', created_by=author)


@override_settings(
    FRONTEND_URL='https://mentoring.example.test',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class ScholarPostNotifiesMentorTests(TestCase):

    def setUp(self):
        self.scholar = make_user('scholar@example.com', role=User.Role.SCHOLAR)
        self.mentor = make_user('mentor@example.com', role=User.Role.MENTOR, notification_email=True)
        make_match(self.scholar, self.mentor)
        self.forum = Forum.objects.create(title='General', visibility=Forum.Visibility.OPEN)
        self.thread = make_thread(self.forum, self.scholar)

    def test_visible_post_notifies_matched_mentor(self):
        mail.outbox = []
        Post.objects.create(
            thread=self.thread, author=self.scholar,
            body='I posted my draft goals, could you take a look?',
            status=Post.Status.VISIBLE,
        )

        notes = Notification.objects.filter(
            user=self.mentor, notification_type=Notification.Type.SCHOLAR_FORUM_POST,
        )
        self.assertEqual(notes.count(), 1)
        note = notes.first()
        self.assertIn('Scholar', note.title)  # names the scholar
        self.assertIn('/forums', note.link)
        # Email dispatched via the N-1 pipeline, debounced by N-3.
        self.assertEqual(len(mail.outbox), 0)
        flush_email_digests_now()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['mentor@example.com'])

    def _mentor_notes(self):
        return Notification.objects.filter(
            user=self.mentor, notification_type=Notification.Type.SCHOLAR_FORUM_POST,
        )

    def test_held_post_notifies_only_on_approval(self):
        """A post held for moderation must not notify until approved."""
        post = Post.objects.create(
            thread=self.thread, author=self.scholar, body='held for review',
            status=Post.Status.FLAGGED,
        )
        self.assertEqual(self._mentor_notes().count(), 0)

        # Admin approves -> visible -> notify now.
        post.status = Post.Status.VISIBLE
        post.save(update_fields=['status'])
        self.assertEqual(self._mentor_notes().count(), 1)

    def test_rejected_post_never_notifies(self):
        post = Post.objects.create(
            thread=self.thread, author=self.scholar, body='blocked content',
            status=Post.Status.HIDDEN,
        )
        post.status = Post.Status.HIDDEN
        post.save(update_fields=['status'])
        self.assertEqual(self._mentor_notes().count(), 0)

    def test_unmatched_mentor_gets_nothing(self):
        other_mentor = make_user('other-mentor@example.com', role=User.Role.MENTOR)
        Post.objects.create(
            thread=self.thread, author=self.scholar, body='hello', status=Post.Status.VISIBLE,
        )
        self.assertFalse(
            Notification.objects.filter(
                user=other_mentor, notification_type=Notification.Type.SCHOLAR_FORUM_POST,
            ).exists()
        )

    def test_no_notification_for_forum_mentor_cannot_see(self):
        """Private forum the mentor is not a member of -> no notification (no leak)."""
        private = Forum.objects.create(title='Private group', visibility=Forum.Visibility.PRIVATE)
        private.members.add(self.scholar)  # mentor deliberately NOT a member
        thread = make_thread(private, self.scholar)

        mail.outbox = []
        Post.objects.create(
            thread=thread, author=self.scholar, body='secret plans', status=Post.Status.VISIBLE,
        )
        self.assertEqual(self._mentor_notes().count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_private_forum_member_mentor_is_notified(self):
        """Control for the visibility test: a member mentor IS notified."""
        private = Forum.objects.create(title='Private group', visibility=Forum.Visibility.PRIVATE)
        private.members.add(self.scholar, self.mentor)
        thread = make_thread(private, self.scholar)

        Post.objects.create(
            thread=thread, author=self.scholar, body='members only', status=Post.Status.VISIBLE,
        )
        self.assertEqual(self._mentor_notes().count(), 1)

    def test_mentor_post_does_not_notify_scholar(self):
        """Only scholar -> mentor; a mentor posting notifies no one via this path."""
        Post.objects.create(
            thread=self.thread, author=self.mentor, body='mentor posting', status=Post.Status.VISIBLE,
        )
        self.assertFalse(
            Notification.objects.filter(
                notification_type=Notification.Type.SCHOLAR_FORUM_POST,
            ).exists()
        )

    def test_api_clean_post_notifies_mentor_end_to_end(self):
        """The real endpoint: scholar posts a clean reply -> mentor notified."""
        ModerationService.invalidate_cache()
        client = APIClient()
        client.force_authenticate(self.scholar)

        mail.outbox = []
        resp = client.post(
            '/api/forums/posts/',
            {'thread': self.thread.pk, 'body': 'Thanks, that really helped me prepare.'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self._mentor_notes().count(), 1)
        flush_email_digests_now()
        self.assertEqual(len(mail.outbox), 1)

    def test_editing_visible_post_does_not_renotify(self):
        post = Post.objects.create(
            thread=self.thread, author=self.scholar, body='original', status=Post.Status.VISIBLE,
        )
        self.assertEqual(self._mentor_notes().count(), 1)

        post.body = 'edited body'
        post.save(update_fields=['body'])
        post.save()  # a full re-save too
        self.assertEqual(self._mentor_notes().count(), 1)
