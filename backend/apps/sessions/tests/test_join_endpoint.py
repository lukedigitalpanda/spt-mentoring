from datetime import timedelta
from urllib.parse import urlparse

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import User
from apps.sessions.models import MentoringSession
from apps.sessions.tests.test_jaas import JAAS_SETTINGS


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class JoinEndpointTest(TestCase):
    def setUp(self):
        self.mentor = User.objects.create_user(
            email='m@example.com', password='x', first_name='Mary', last_name='Mentor', role='mentor', username='m')
        self.scholar = User.objects.create_user(
            email='s@example.com', password='x', first_name='Sam', last_name='Scholar', role='scholar', username='s')
        self.outsider = User.objects.create_user(
            email='o@example.com', password='x', first_name='Otto', last_name='Outsider', role='mentor', username='o')
        now = timezone.now()
        self.session = MentoringSession.objects.create(
            mentor=self.mentor, scholar=self.scholar,
            start_time=now - timedelta(minutes=1), end_time=now + timedelta(minutes=59),
            status=MentoringSession.Status.CONFIRMED)
        self.url = f'/api/sessions/sessions/{self.session.pk}/join/'

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_outsider_cannot_see_session(self):
        # get_queryset scopes non-staff to their own sessions -> 404.
        resp = self._client(self.outsider).get(self.url)
        self.assertEqual(resp.status_code, 404)

    @override_settings(**JAAS_SETTINGS)
    def test_participant_gets_jaas_url(self):
        resp = self._client(self.scholar).get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(urlparse(resp.data['url']).netloc, '8x8.vc')

    @override_settings(JAAS_APP_ID='', JAAS_KID='', JAAS_PRIVATE_KEY='', JAAS_ENABLED=False)
    def test_falls_back_to_jitsi_when_unconfigured(self):
        resp = self._client(self.mentor).get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['url'], self.session.meeting_url)
        self.assertIn('meet.jit.si', resp.data['url'])

    @override_settings(**JAAS_SETTINGS)
    def test_not_joinable_is_rejected(self):
        self.session.start_time = timezone.now() + timedelta(hours=2)
        self.session.end_time = timezone.now() + timedelta(hours=3)
        self.session.save(update_fields=['start_time', 'end_time'])
        resp = self._client(self.mentor).get(self.url)
        self.assertEqual(resp.status_code, 409)
