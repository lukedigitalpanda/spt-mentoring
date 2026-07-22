"""
Regression tests for shared documents (UAT P2-3).

Round-2 root cause: the '' (catch-all) router prefix was registered before
'shared-documents', so /api/resources/shared-documents/ resolved to the
Resource detail route and every upload/list call failed.  These tests exercise
the real URLs end-to-end so a routing regression cannot pass silently.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User
from .models import SharedDocument


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


def docx_upload(name='notes.docx'):
    return SimpleUploadedFile(
        name, b'PK\x03\x04 fake docx content',
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )


class SharedDocumentTests(TestCase):
    def setUp(self):
        self.scholar = make_user('scholar-doc@example.com', role=User.Role.SCHOLAR)
        self.mentor = make_user('mentor-doc@example.com', role=User.Role.MENTOR)
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.scholar)

    def _upload(self, **extra):
        data = {'file': docx_upload(), 'filename': 'notes.docx', 'shared_with': self.mentor.pk}
        data.update(extra)
        return self.client_api.post('/api/resources/shared-documents/', data, format='multipart')

    def test_docx_upload_succeeds_via_real_url(self):
        resp = self._upload()
        self.assertEqual(resp.status_code, 201, resp.content)
        doc = SharedDocument.objects.get()
        self.assertEqual(doc.shared_by, self.scholar)
        self.assertEqual(doc.shared_with, self.mentor)

    def test_upload_by_recipient_email(self):
        data = {'file': docx_upload(), 'filename': 'notes.docx',
                'shared_with_email': self.mentor.email}
        resp = self.client_api.post('/api/resources/shared-documents/', data, format='multipart')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(SharedDocument.objects.get().shared_with, self.mentor)

    def test_upload_without_recipient_rejected(self):
        data = {'file': docx_upload(), 'filename': 'notes.docx'}
        resp = self.client_api.post('/api/resources/shared-documents/', data, format='multipart')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SharedDocument.objects.count(), 0)

    def test_uploader_recipient_and_admin_can_all_see_document(self):
        self._upload()
        for u in (self.scholar, self.mentor):
            client = APIClient()
            client.force_authenticate(u)
            resp = client.get('/api/resources/shared-documents/')
            self.assertEqual(resp.data['count'], 1, f'{u.email} cannot see the document')

        admin = make_user('admin-doc@example.com', role=User.Role.ADMIN, is_staff=True)
        client = APIClient()
        client.force_authenticate(admin)
        resp = client.get('/api/resources/shared-documents/')
        self.assertEqual(resp.data['count'], 1, 'admin cannot see the document')

    def test_unrelated_user_cannot_see_document(self):
        self._upload()
        outsider = make_user('outsider-doc@example.com', role=User.Role.SCHOLAR)
        client = APIClient()
        client.force_authenticate(outsider)
        resp = client.get('/api/resources/shared-documents/')
        self.assertEqual(resp.data['count'], 0)

    def test_latest_upload_appears_first_on_page_one(self):
        """P2-A: a freshly uploaded document must appear at the top of page 1 so
        the uploader always sees it (the profile page only fetches page 1)."""
        first = self._upload(filename='first.docx')
        self.assertEqual(first.status_code, 201, first.content)
        second = self._upload(filename='second.docx')
        self.assertEqual(second.status_code, 201, second.content)

        resp = self.client_api.get('/api/resources/shared-documents/')
        results = resp.data['results']
        self.assertEqual(results[0]['filename'], 'second.docx')
        # The uploader can see their own most recent upload.
        self.assertIn('second.docx', [r['filename'] for r in results])
