from datetime import timedelta
from urllib.parse import urlparse, parse_qs

import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.users.models import User
from apps.sessions.models import MentoringSession
from apps.sessions import jaas


def _make_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


PRIVATE_PEM, PUBLIC_PEM = _make_keypair()

JAAS_SETTINGS = dict(
    JAAS_APP_ID='vpaas-magic-cookie-test',
    JAAS_KID='vpaas-magic-cookie-test/abc123',
    JAAS_PRIVATE_KEY=PRIVATE_PEM,
    JAAS_ENABLED=True,
)


class JaaSTest(TestCase):
    def setUp(self):
        self.mentor = User.objects.create_user(
            email='m@example.com', password='x', first_name='Mary', last_name='Mentor', role='mentor', username='m')
        self.scholar = User.objects.create_user(
            email='s@example.com', password='x', first_name='Sam', last_name='Scholar', role='scholar', username='s')
        now = timezone.now()
        self.session = MentoringSession.objects.create(
            mentor=self.mentor, scholar=self.scholar,
            start_time=now, end_time=now + timedelta(hours=1),
            status=MentoringSession.Status.CONFIRMED)

    @override_settings(JAAS_APP_ID='', JAAS_KID='', JAAS_PRIVATE_KEY='', JAAS_ENABLED=False)
    def test_is_configured_false_when_blank(self):
        self.assertFalse(jaas.is_configured())

    @override_settings(**JAAS_SETTINGS)
    def test_is_configured_true_when_set(self):
        self.assertTrue(jaas.is_configured())

    @override_settings(**JAAS_SETTINGS)
    def test_build_join_url_shape(self):
        url = jaas.build_join_url(self.session, self.mentor)
        parsed = urlparse(url)
        self.assertEqual(parsed.scheme, 'https')
        self.assertEqual(parsed.netloc, '8x8.vc')
        self.assertTrue(parsed.path.startswith('/vpaas-magic-cookie-test/'))
        self.assertIn('jwt', parse_qs(parsed.query))

    @override_settings(**JAAS_SETTINGS)
    def test_token_claims_decode_with_public_key(self):
        url = jaas.build_join_url(self.session, self.mentor)
        token = parse_qs(urlparse(url).query)['jwt'][0]
        claims = pyjwt.decode(token, PUBLIC_PEM, algorithms=['RS256'], audience='jitsi')
        self.assertEqual(claims['iss'], 'chat')
        self.assertEqual(claims['sub'], 'vpaas-magic-cookie-test')
        self.assertEqual(claims['room'], self.session.room_name)
        self.assertEqual(claims['context']['user']['moderator'], 'true')
        self.assertEqual(claims['context']['user']['email'], 'm@example.com')

    @override_settings(**JAAS_SETTINGS)
    def test_token_kid_header_set(self):
        url = jaas.build_join_url(self.session, self.scholar)
        token = parse_qs(urlparse(url).query)['jwt'][0]
        header = pyjwt.get_unverified_header(token)
        self.assertEqual(header['kid'], 'vpaas-magic-cookie-test/abc123')
        self.assertEqual(header['alg'], 'RS256')
