"""
Tests for the in-app password change endpoint.

    POST /api/users/me/change-password/   { new_password, confirm_password }

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test apps.users.tests --verbosity=2
"""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User


def make_user(**kwargs):
    defaults = dict(
        username='mentor@example.com',
        email='mentor@example.com',
        first_name='Demo',
        last_name='Mentor',
        role=User.Role.MENTOR,
        is_active=True,
        is_verified=True,
        notification_email=False,
    )
    defaults.update(kwargs)
    user = User(**defaults)
    user.set_password('OldPass123!xyz')
    user.save()
    return user


URL = '/api/users/me/change-password/'


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_valid_change_updates_password(self):
        resp = self.client.post(
            URL,
            {'new_password': 'NewPass987!abc', 'confirm_password': 'NewPass987!abc'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass987!abc'))
        self.assertFalse(self.user.check_password('OldPass123!xyz'))

    def test_mismatched_passwords_rejected(self):
        resp = self.client.post(
            URL,
            {'new_password': 'NewPass987!abc', 'confirm_password': 'Different987!abc'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123!xyz'))

    def test_weak_password_rejected(self):
        resp = self.client.post(
            URL,
            {'new_password': '123', 'confirm_password': '123'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123!xyz'))

    def test_unauthenticated_rejected(self):
        client = APIClient()
        resp = client.post(
            URL,
            {'new_password': 'NewPass987!abc', 'confirm_password': 'NewPass987!abc'},
            format='json',
        )
        self.assertEqual(resp.status_code, 401, resp.content)
