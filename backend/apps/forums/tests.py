"""
Forum post moderation tests (FOR-01/02/03/04/05).

Forum posts run through the same ModerationService pipeline as direct messages,
so the full flagged-terms list (profanity, slurs, contact details) applies.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User
from apps.moderation.models import ModerationTerm
from apps.moderation.service import ModerationService
from .models import Forum, Thread, Post


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


class ForumPostModerationTests(TestCase):
    def setUp(self):
        ModerationService.invalidate_cache()
        self.user = make_user('forum-scholar@example.com')
        self.forum = Forum.objects.create(title='General', visibility=Forum.Visibility.OPEN)
        self.thread = Thread.objects.create(forum=self.forum, title='Hello', created_by=self.user)
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.user)

    def tearDown(self):
        ModerationService.invalidate_cache()

    def _post(self, body):
        return self.client_api.post(
            '/api/forums/posts/', {'thread': self.thread.pk, 'body': body}, format='json'
        )

    def test_clean_post_is_visible(self):
        """FOR-01: a clean post publishes immediately."""
        resp = self._post('Looking forward to the next session, thanks for the advice.')
        self.assertEqual(resp.status_code, 201, resp.content)
        post = Post.objects.latest('created_at')
        self.assertEqual(post.status, Post.Status.VISIBLE)

    def test_profanity_post_is_flagged(self):
        """FOR-03/04/05: a post with a flagged term from the imported list is held for review."""
        ModerationTerm.objects.create(
            term='shit', match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.MEDIUM, source='bulk_import_v1', is_active=True,
        )
        ModerationService.invalidate_cache()
        resp = self._post('this is shit')
        self.assertEqual(resp.status_code, 202, resp.content)
        self.assertEqual(resp.data['moderation_status'], 'pending_review')
        post = Post.objects.latest('created_at')
        self.assertEqual(post.status, Post.Status.FLAGGED)

    def test_contact_detail_post_is_flagged_not_blocked(self):
        """FOR-02: a contact detail (bare @) is held for review, never hard-blocked."""
        resp = self._post('email me at me@example.com')
        self.assertEqual(resp.status_code, 202, resp.content)
        post = Post.objects.latest('created_at')
        self.assertEqual(post.status, Post.Status.FLAGGED)

    def test_blocked_term_post_is_hidden(self):
        """A genuinely blocked (CRITICAL) term hides the post outright."""
        ModerationTerm.objects.create(
            term='murder', match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.CRITICAL, source='bulk_import_v1', is_active=True,
        )
        ModerationService.invalidate_cache()
        resp = self._post('I want to murder')
        self.assertEqual(resp.status_code, 400, resp.content)
        post = Post.objects.latest('created_at')
        self.assertEqual(post.status, Post.Status.HIDDEN)


class ForumPostAttachmentTests(TestCase):
    """Task 8: forum posts share the same attachment validator as chat messages."""

    def setUp(self):
        ModerationService.invalidate_cache()
        self.user = make_user('forum-attach-scholar@example.com')
        self.forum = Forum.objects.create(title='General', visibility=Forum.Visibility.OPEN)
        self.thread = Thread.objects.create(forum=self.forum, title='Hello', created_by=self.user)
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.user)

    def tearDown(self):
        ModerationService.invalidate_cache()

    def test_zip_attachment_is_accepted(self):
        """A clean post with a small ZIP attachment publishes and returns the attachment URL."""
        upload = SimpleUploadedFile(
            'notes.zip', b'PK\x03\x04 fake zip content', content_type='application/zip'
        )
        resp = self.client_api.post(
            '/api/forums/posts/',
            {'thread': self.thread.pk, 'body': 'Sharing some notes, see attached.', 'attachment': upload},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(resp.data.get('attachment'))
        post = Post.objects.latest('created_at')
        self.assertEqual(post.status, Post.Status.VISIBLE)
        self.assertTrue(post.attachment.name.endswith('.zip'))

    def test_exe_attachment_is_rejected(self):
        upload = SimpleUploadedFile(
            'virus.exe', b'MZ fake exe content', content_type='application/x-msdownload'
        )
        resp = self.client_api.post(
            '/api/forums/posts/',
            {'thread': self.thread.pk, 'body': 'See attached.', 'attachment': upload},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 400, resp.content)
