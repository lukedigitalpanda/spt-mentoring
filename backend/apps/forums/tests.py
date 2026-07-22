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


class PostEditTests(TestCase):
    """Task 13 (P2-4): forum post edits are author-or-staff only and always
    re-moderated; the previously unmoderated PATCH/PUT/DELETE holes are closed."""

    def setUp(self):
        ModerationService.invalidate_cache()
        self.author = make_user('post-author@example.com')
        self.other = make_user('post-other@example.com')
        self.staff = make_user('post-staff@example.com', role=User.Role.ADMIN, is_staff=True)
        self.forum = Forum.objects.create(title='General', visibility=Forum.Visibility.OPEN)
        self.thread = Thread.objects.create(forum=self.forum, title='Hello', created_by=self.author)
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.author)

    def tearDown(self):
        ModerationService.invalidate_cache()

    def _create_visible_post(self):
        resp = self.client_api.post(
            '/api/forums/posts/',
            {'thread': self.thread.pk, 'body': 'A perfectly clean first draft.'},
            format='json',
        )
        assert resp.status_code == 201, resp.content
        return Post.objects.get(pk=resp.data['id'])

    def _patch(self, post_id, body, client=None):
        return (client or self.client_api).patch(
            f'/api/forums/posts/{post_id}/', {'body': body}, format='json'
        )

    def test_author_edit_clean_stays_visible_with_edited_marker(self):
        post = self._create_visible_post()
        self.assertIsNone(post.edited_at)
        history_before = post.history.count()

        edit = self._patch(post.pk, 'A clean improved second draft.')
        self.assertEqual(edit.status_code, 200, edit.content)
        self.assertEqual(edit.data['body'], 'A clean improved second draft.')
        self.assertIsNotNone(edit.data['edited_at'])

        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.VISIBLE)
        self.assertIsNotNone(post.edited_at)
        self.assertGreater(post.history.count(), history_before)

    def test_author_edit_to_flagged_term_is_held(self):
        ModerationTerm.objects.create(
            term='shit', match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.MEDIUM, source='bulk_import_v1', is_active=True,
        )
        ModerationService.invalidate_cache()
        post = self._create_visible_post()
        edit = self._patch(post.pk, 'this is shit')
        self.assertEqual(edit.status_code, 202, edit.content)
        self.assertEqual(edit.data['moderation_status'], 'pending_review')
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.FLAGGED)
        self.assertIsNotNone(post.edited_at)

    def test_author_edit_to_blocked_term_is_hidden(self):
        ModerationTerm.objects.create(
            term='murder', match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.CRITICAL, source='bulk_import_v1', is_active=True,
        )
        ModerationService.invalidate_cache()
        post = self._create_visible_post()
        edit = self._patch(post.pk, 'I want to murder')
        self.assertEqual(edit.status_code, 400, edit.content)
        self.assertEqual(edit.data['moderation_status'], 'blocked')
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.HIDDEN)

    def test_non_author_cannot_edit(self):
        post = self._create_visible_post()
        other_client = APIClient()
        other_client.force_authenticate(self.other)
        edit = self._patch(post.pk, 'Hijacked body', client=other_client)
        self.assertEqual(edit.status_code, 403, edit.content)
        self.assertEqual(edit.data['detail'], 'You can only edit your own posts.')
        post.refresh_from_db()
        self.assertEqual(post.body, 'A perfectly clean first draft.')

    def test_staff_can_edit_and_edit_is_remoderated(self):
        post = self._create_visible_post()
        staff_client = APIClient()
        staff_client.force_authenticate(self.staff)
        edit = self._patch(post.pk, 'Tidied up by staff.', client=staff_client)
        self.assertEqual(edit.status_code, 200, edit.content)
        post.refresh_from_db()
        self.assertEqual(post.body, 'Tidied up by staff.')
        self.assertEqual(post.status, Post.Status.VISIBLE)

    def test_empty_body_rejected(self):
        post = self._create_visible_post()
        edit = self._patch(post.pk, '   ')
        self.assertEqual(edit.status_code, 400, edit.content)
        self.assertEqual(edit.data['detail'], 'Post body cannot be empty.')

    def test_put_is_rejected(self):
        post = self._create_visible_post()
        put = self.client_api.put(
            f'/api/forums/posts/{post.pk}/',
            {'thread': self.thread.pk, 'body': 'Full replacement'},
            format='json',
        )
        self.assertEqual(put.status_code, 405, put.content)

    def test_non_admin_cannot_delete(self):
        post = self._create_visible_post()
        other_client = APIClient()
        other_client.force_authenticate(self.other)
        delete = other_client.delete(f'/api/forums/posts/{post.pk}/')
        self.assertEqual(delete.status_code, 403, delete.content)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())


class HeldPostVisibilityAndResubmitTests(TestCase):
    """P2-4 follow-up: authors must be able to see and fix their own held
    (flagged) or hidden (blocked) posts, mirroring Task 5's messaging rule.
    Other participants must never see held/hidden content."""

    def setUp(self):
        ModerationService.invalidate_cache()
        ModerationTerm.objects.create(
            term='shit', match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.MEDIUM, source='bulk_import_v1', is_active=True,
        )
        ModerationTerm.objects.create(
            term='murder', match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.CRITICAL, source='bulk_import_v1', is_active=True,
        )
        ModerationService.invalidate_cache()
        self.author = make_user('held-author@example.com')
        self.other = make_user('held-other@example.com')
        self.forum = Forum.objects.create(title='General', visibility=Forum.Visibility.OPEN)
        self.thread = Thread.objects.create(forum=self.forum, title='Hello', created_by=self.author)
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.author)

    def tearDown(self):
        ModerationService.invalidate_cache()

    def _create_post(self, body, expect_status):
        resp = self.client_api.post(
            '/api/forums/posts/', {'thread': self.thread.pk, 'body': body}, format='json'
        )
        assert resp.status_code == expect_status, resp.content
        return Post.objects.latest('created_at')

    def _thread_listing_ids(self, client):
        resp = client.get(f'/api/forums/posts/?thread={self.thread.pk}')
        data = resp.data['results'] if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        return [p['id'] for p in data]

    def test_author_sees_own_flagged_post_but_others_do_not(self):
        post = self._create_post('this is shit', 202)
        self.assertEqual(post.status, Post.Status.FLAGGED)

        self.assertIn(post.pk, self._thread_listing_ids(self.client_api))

        other_client = APIClient()
        other_client.force_authenticate(self.other)
        self.assertNotIn(post.pk, self._thread_listing_ids(other_client))

    def test_author_edits_own_flagged_post_to_clean_becomes_visible(self):
        post = self._create_post('this is shit', 202)
        edit = self.client_api.patch(
            f'/api/forums/posts/{post.pk}/',
            {'body': 'Apologies, here is a polite version.'}, format='json',
        )
        self.assertEqual(edit.status_code, 200, edit.content)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.VISIBLE)
        self.assertIsNotNone(post.edited_at)

        # Now visible to everyone.
        other_client = APIClient()
        other_client.force_authenticate(self.other)
        self.assertIn(post.pk, self._thread_listing_ids(other_client))

    def test_author_edits_own_hidden_post_and_is_rescreened(self):
        post = self._create_post('I want to murder', 400)
        self.assertEqual(post.status, Post.Status.HIDDEN)

        # Still held when the edit still trips a flagged term.
        edit = self.client_api.patch(
            f'/api/forums/posts/{post.pk}/', {'body': 'this is shit'}, format='json',
        )
        self.assertEqual(edit.status_code, 202, edit.content)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.FLAGGED)

        # A clean re-edit releases it.
        edit = self.client_api.patch(
            f'/api/forums/posts/{post.pk}/', {'body': 'Entirely clean now.'}, format='json',
        )
        self.assertEqual(edit.status_code, 200, edit.content)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.VISIBLE)

    def test_other_user_cannot_edit_or_fetch_held_post(self):
        post = self._create_post('this is shit', 202)
        other_client = APIClient()
        other_client.force_authenticate(self.other)
        edit = other_client.patch(
            f'/api/forums/posts/{post.pk}/', {'body': 'Hijack attempt'}, format='json',
        )
        self.assertEqual(edit.status_code, 404, edit.content)
