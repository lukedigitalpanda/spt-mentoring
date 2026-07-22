"""
Security hotfix: MentoringMatchViewSet previously exposed every match
(including free-text notes and matched_by) to any authenticated user via
list/retrieve, and its admin-only action set omitted 'partial_update', so
any authenticated user could PATCH any match (flip is_active, rewrite
notes, reassign FKs).

Run with:
    docker compose exec -T backend python manage.py test apps.users -v 1
"""
from rest_framework.test import APIClient
from django.test import TestCase

from apps.users.models import User, MentoringMatch


def make_user(email, role, **kwargs):
    defaults = dict(
        username=email.split('@')[0],
        email=email,
        first_name=email.split('@')[0].title(),
        last_name='Test',
        role=role,
        is_active=True,
        is_verified=True,
    )
    defaults.update(kwargs)
    return User.objects.create(**defaults)


class MentoringMatchAccessTest(TestCase):
    def setUp(self):
        self.mentor = make_user('mentor@example.com', User.Role.MENTOR)
        self.scholar = make_user('scholar@example.com', User.Role.SCHOLAR)
        self.other_mentor = make_user('mentor2@example.com', User.Role.MENTOR)
        self.other_scholar = make_user('scholar2@example.com', User.Role.SCHOLAR)
        self.admin = make_user('admin@example.com', User.Role.ADMIN, is_staff=True)

        self.own_match = MentoringMatch.objects.create(
            mentor=self.mentor, scholar=self.scholar, is_active=True, notes='confidential note')
        self.other_match = MentoringMatch.objects.create(
            mentor=self.other_mentor, scholar=self.other_scholar, is_active=True, notes='someone else')

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    # ── list/retrieve scoping ────────────────────────────────────────────
    def test_non_staff_sees_only_own_matches_as_mentor(self):
        resp = self._client(self.mentor).get('/api/users/matches/')
        self.assertEqual(resp.status_code, 200, resp.data)
        ids = [m['id'] for m in resp.data['results']] if 'results' in resp.data else [m['id'] for m in resp.data]
        self.assertIn(self.own_match.id, ids)
        self.assertNotIn(self.other_match.id, ids)

    def test_non_staff_sees_only_own_matches_as_scholar(self):
        resp = self._client(self.scholar).get('/api/users/matches/')
        self.assertEqual(resp.status_code, 200, resp.data)
        ids = [m['id'] for m in resp.data['results']] if 'results' in resp.data else [m['id'] for m in resp.data]
        self.assertIn(self.own_match.id, ids)
        self.assertNotIn(self.other_match.id, ids)

    def test_non_staff_cannot_retrieve_someone_elses_match(self):
        resp = self._client(self.mentor).get(f'/api/users/matches/{self.other_match.id}/')
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_uninvolved_user_sees_no_matches(self):
        uninvolved = make_user('bystander@example.com', User.Role.SCHOLAR)
        resp = self._client(uninvolved).get('/api/users/matches/')
        self.assertEqual(resp.status_code, 200, resp.data)
        ids = [m['id'] for m in resp.data['results']] if 'results' in resp.data else [m['id'] for m in resp.data]
        self.assertEqual(ids, [])

    def test_staff_list_sees_all_matches(self):
        resp = self._client(self.admin).get('/api/users/matches/')
        self.assertEqual(resp.status_code, 200, resp.data)
        ids = [m['id'] for m in resp.data['results']] if 'results' in resp.data else [m['id'] for m in resp.data]
        self.assertIn(self.own_match.id, ids)
        self.assertIn(self.other_match.id, ids)

    # ── write scoping ─────────────────────────────────────────────────────
    def test_non_staff_patch_on_someone_elses_match_is_403(self):
        resp = self._client(self.other_mentor).patch(
            f'/api/users/matches/{self.own_match.id}/', {'is_active': False}, format='json')
        self.assertEqual(resp.status_code, 403, resp.data)
        self.own_match.refresh_from_db()
        self.assertTrue(self.own_match.is_active)

    def test_non_staff_patch_on_own_match_is_still_403(self):
        # Even a party to the match cannot self-service edit it - admin only.
        resp = self._client(self.mentor).patch(
            f'/api/users/matches/{self.own_match.id}/', {'notes': 'trying to edit'}, format='json')
        self.assertEqual(resp.status_code, 403, resp.data)

    def test_staff_patch_works(self):
        resp = self._client(self.admin).patch(
            f'/api/users/matches/{self.own_match.id}/', {'is_active': False}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.own_match.refresh_from_db()
        self.assertFalse(self.own_match.is_active)
