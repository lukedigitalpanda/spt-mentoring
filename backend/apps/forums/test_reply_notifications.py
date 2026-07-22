"""
Tests for sprint item P2-3b: notify earlier thread participants when a reply
becomes visible, with debounced email.

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test apps.forums --verbosity=2
"""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone

from apps.users.models import User, MentoringMatch
from apps.notifications.models import Notification
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


def make_thread(forum, author, title='Study plans'):
    return Thread.objects.create(forum=forum, title=title, created_by=author)


@override_settings(
    FRONTEND_URL='https://mentoring.example.test',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class ForumReplyNotifiesParticipantsTests(TestCase):

    def setUp(self):
        self.scholar = make_user('scholar@example.com', role=User.Role.SCHOLAR, notification_email=True)
        self.mentor = make_user('mentor@example.com', role=User.Role.MENTOR, notification_email=True)
        self.forum = Forum.objects.create(title='General', visibility=Forum.Visibility.OPEN)
        self.thread = make_thread(self.forum, self.scholar)

    def _scholar_reply_notes(self):
        return Notification.objects.filter(
            user=self.scholar, notification_type=Notification.Type.FORUM_REPLY,
        )

    def test_mentor_reply_notifies_scholar_thread_creator(self):
        mail.outbox = []
        Post.objects.create(
            thread=self.thread, author=self.mentor,
            body='Great progress, keep it up!',
            status=Post.Status.VISIBLE,
        )

        notes = self._scholar_reply_notes()
        self.assertEqual(notes.count(), 1)
        note = notes.first()
        self.assertEqual(note.title, f'New reply in "{self.thread.title}"')
        self.assertEqual(note.body, 'Great progress, keep it up!')
        self.assertIn('/forums', note.link)

        self.assertEqual(len(mail.outbox), 0)
        flush_email_digests_now()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['scholar@example.com'])

    def test_reply_author_not_notified(self):
        Post.objects.create(
            thread=self.thread, author=self.mentor,
            body='hello', status=Post.Status.VISIBLE,
        )
        self.assertFalse(
            Notification.objects.filter(
                user=self.mentor, notification_type=Notification.Type.FORUM_REPLY,
            ).exists()
        )

    def test_fires_once_even_on_resave(self):
        post = Post.objects.create(
            thread=self.thread, author=self.mentor,
            body='original', status=Post.Status.VISIBLE,
        )
        self.assertEqual(self._scholar_reply_notes().count(), 1)

        post.body = 'edited body'
        post.save(update_fields=['body'])
        post.save()  # a full re-save too
        self.assertEqual(self._scholar_reply_notes().count(), 1)

    def test_user_without_forum_visibility_not_notified(self):
        """A thread participant who lost (or never had) visibility of the
        forum must never be notified, even though they authored an earlier
        post in the thread; a participant who still has visibility is."""
        private = Forum.objects.create(title='Private group', visibility=Forum.Visibility.PRIVATE)
        outsider = make_user('outsider@example.com', role=User.Role.MENTOR)
        # Both are members when they post, establishing them as participants.
        private.members.add(self.scholar, outsider)
        thread = make_thread(private, self.scholar)
        Post.objects.create(
            thread=thread, author=outsider,
            body='outsider post', status=Post.Status.VISIBLE,
        )
        # Outsider then loses membership before the mentor's reply arrives.
        private.members.remove(outsider)
        private.members.add(self.mentor)

        Post.objects.create(
            thread=thread, author=self.mentor,
            body='reply in private thread', status=Post.Status.VISIBLE,
        )
        # Outsider: authored an earlier post but no longer has visibility -> skipped.
        self.assertFalse(
            Notification.objects.filter(
                user=outsider, notification_type=Notification.Type.FORUM_REPLY,
            ).exists()
        )
        # Scholar: thread creator, still has visibility -> notified.
        self.assertTrue(
            Notification.objects.filter(
                user=self.scholar, notification_type=Notification.Type.FORUM_REPLY,
            ).exists()
        )

    def test_notification_email_false_gets_inapp_but_no_email(self):
        self.scholar.notification_email = False
        self.scholar.save(update_fields=['notification_email'])

        mail.outbox = []
        Post.objects.create(
            thread=self.thread, author=self.mentor,
            body='hello there', status=Post.Status.VISIBLE,
        )
        self.assertEqual(self._scholar_reply_notes().count(), 1)
        flush_email_digests_now()
        self.assertEqual(len(mail.outbox), 0)

    def test_no_double_notification_for_matched_mentor_already_notified_of_scholar_post(self):
        """A matched mentor who already got SCHOLAR_FORUM_POST for this exact
        post (because they're also a thread participant) must not also get
        FORUM_REPLY for it."""
        make_match(self.scholar, self.mentor)
        # Mentor posts first, becoming a thread participant. (This also
        # queues an unrelated FORUM_REPLY email to the scholar, as thread
        # creator; flush it now so it doesn't leak into the assertions below.)
        Post.objects.create(
            thread=self.thread, author=self.mentor,
            body='first mentor post', status=Post.Status.VISIBLE,
        )
        self.assertEqual(
            Notification.objects.filter(
                user=self.mentor, notification_type=Notification.Type.FORUM_REPLY,
            ).count(),
            0,
        )
        flush_email_digests_now()

        mail.outbox = []
        # Scholar now replies -> triggers both notify_mentors_of_scholar_post
        # (matched mentor) and notify_thread_participants_of_reply (mentor is
        # a prior participant). Mentor must get exactly one notification.
        Post.objects.create(
            thread=self.thread, author=self.scholar,
            body='scholar reply', status=Post.Status.VISIBLE,
        )

        scholar_post_notes = Notification.objects.filter(
            user=self.mentor, notification_type=Notification.Type.SCHOLAR_FORUM_POST,
        )
        reply_notes = Notification.objects.filter(
            user=self.mentor, notification_type=Notification.Type.FORUM_REPLY,
        )
        self.assertEqual(scholar_post_notes.count(), 1)
        self.assertEqual(reply_notes.count(), 0)

        flush_email_digests_now()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['mentor@example.com'])
