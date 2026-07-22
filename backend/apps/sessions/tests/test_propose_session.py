from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import User, MentoringMatch
from apps.sessions.models import AvailabilitySlot, MentoringSession
from apps.notifications.models import Notification


class ProposeSessionTest(TestCase):
    """Task 19: mentors can propose a session at a specific date/time for
    scholar confirmation."""

    def setUp(self):
        self.mentor = User.objects.create_user(
            username='mentor', email='m@example.com', password='x',
            first_name='Mary', last_name='Mentor', role='mentor')
        self.scholar = User.objects.create_user(
            username='scholar', email='s@example.com', password='x',
            first_name='Sam', last_name='Scholar', role='scholar')
        self.other_scholar = User.objects.create_user(
            username='scholar2', email='s2@example.com', password='x',
            first_name='Sue', last_name='Scholar', role='scholar')
        MentoringMatch.objects.create(mentor=self.mentor, scholar=self.scholar, is_active=True)

        self.start = timezone.now().replace(microsecond=0) + timedelta(days=2)
        self.end = self.start + timedelta(hours=1)
        self.url = '/api/sessions/sessions/propose/'

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def _payload(self, **overrides):
        data = {
            'scholar': self.scholar.id,
            'start_time': self.start.isoformat(),
            'end_time': self.end.isoformat(),
            'title': 'Careers chat',
            'agenda': 'Talk about internships',
        }
        data.update(overrides)
        return data

    # ── Happy path ──────────────────────────────────────────────────────
    def test_matched_mentor_can_propose_session(self):
        resp = self._client(self.mentor).post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

        session = MentoringSession.objects.get(pk=resp.data['id'])
        self.assertEqual(session.status, MentoringSession.Status.PENDING)
        self.assertEqual(session.created_by, self.mentor)
        self.assertEqual(session.mentor, self.mentor)
        self.assertEqual(session.scholar, self.scholar)
        self.assertEqual(session.title, 'Careers chat')

        self.assertIsNotNone(session.slot)
        self.assertTrue(session.slot.is_booked)
        self.assertEqual(session.slot.mentor, self.mentor)

        self.assertTrue(
            Notification.objects.filter(
                user=self.scholar, notification_type='session_request',
            ).exists()
        )

    def test_propose_does_not_merge_into_other_availability_slots(self):
        # An adjoining unbooked slot exists for the mentor; the proposed
        # session's slot must never absorb it (or vice versa).
        AvailabilitySlot.objects.create(
            mentor=self.mentor, is_booked=False,
            start_time=self.start - timedelta(minutes=30),
            end_time=self.start,
        )
        resp = self._client(self.mentor).post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

        self.assertEqual(AvailabilitySlot.objects.filter(mentor=self.mentor).count(), 2)
        proposed_slot = MentoringSession.objects.get(pk=resp.data['id']).slot
        self.assertEqual(proposed_slot.start_time, self.start)
        self.assertEqual(proposed_slot.end_time, self.end)

    # ── Authorisation ───────────────────────────────────────────────────
    def test_propose_to_unmatched_scholar_is_403(self):
        resp = self._client(self.mentor).post(
            self.url, self._payload(scholar=self.other_scholar.id), format='json')
        self.assertEqual(resp.status_code, 403, resp.data)
        self.assertFalse(MentoringSession.objects.exists())

    def test_non_mentor_caller_is_403(self):
        resp = self._client(self.scholar).post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, 403, resp.data)
        self.assertFalse(MentoringSession.objects.exists())

    # ── Validation ──────────────────────────────────────────────────────
    def test_past_start_time_is_400(self):
        past = timezone.now() - timedelta(days=1)
        resp = self._client(self.mentor).post(
            self.url,
            self._payload(start_time=past.isoformat(), end_time=(past + timedelta(hours=1)).isoformat()),
            format='json',
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertFalse(MentoringSession.objects.exists())

    def test_end_before_start_is_400(self):
        resp = self._client(self.mentor).post(
            self.url,
            self._payload(start_time=self.end.isoformat(), end_time=self.start.isoformat()),
            format='json',
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertFalse(MentoringSession.objects.exists())


class ConfirmSessionTest(TestCase):
    """The party who did NOT create a pending session confirms it. Legacy
    rows with created_by=None keep the original mentor-confirms behaviour."""

    def setUp(self):
        self.mentor = User.objects.create_user(
            username='mentor', email='m@example.com', password='x',
            first_name='Mary', last_name='Mentor', role='mentor')
        self.scholar = User.objects.create_user(
            username='scholar', email='s@example.com', password='x',
            first_name='Sam', last_name='Scholar', role='scholar')
        MentoringMatch.objects.create(mentor=self.mentor, scholar=self.scholar, is_active=True)
        self.start = timezone.now().replace(microsecond=0) + timedelta(days=2)
        self.end = self.start + timedelta(hours=1)

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_scholar_confirms_mentor_proposed_session(self):
        propose = self._client(self.mentor).post('/api/sessions/sessions/propose/', {
            'scholar': self.scholar.id,
            'start_time': self.start.isoformat(),
            'end_time': self.end.isoformat(),
            'title': 'Careers chat',
        }, format='json')
        self.assertEqual(propose.status_code, 201, propose.data)
        session_id = propose.data['id']

        resp = self._client(self.scholar).post(f'/api/sessions/sessions/{session_id}/confirm/')
        self.assertEqual(resp.status_code, 200, resp.data)
        session = MentoringSession.objects.get(pk=session_id)
        self.assertEqual(session.status, MentoringSession.Status.CONFIRMED)

    def test_mentor_cannot_confirm_own_proposal(self):
        propose = self._client(self.mentor).post('/api/sessions/sessions/propose/', {
            'scholar': self.scholar.id,
            'start_time': self.start.isoformat(),
            'end_time': self.end.isoformat(),
            'title': 'Careers chat',
        }, format='json')
        self.assertEqual(propose.status_code, 201, propose.data)
        session_id = propose.data['id']

        resp = self._client(self.mentor).post(f'/api/sessions/sessions/{session_id}/confirm/')
        self.assertEqual(resp.status_code, 403, resp.data)
        session = MentoringSession.objects.get(pk=session_id)
        self.assertEqual(session.status, MentoringSession.Status.PENDING)

    def test_mentor_confirms_scholar_booked_session_regression(self):
        slot = AvailabilitySlot.objects.create(
            mentor=self.mentor, start_time=self.start, end_time=self.end, is_booked=False)
        resp = self._client(self.scholar).post('/api/sessions/sessions/', {
            'mentor': self.mentor.id, 'scholar': self.scholar.id, 'slot': slot.id,
            'title': 'Booked by scholar', 'start_time': self.start.isoformat(),
            'end_time': self.end.isoformat(),
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        session_id = resp.data['id']

        confirm = self._client(self.mentor).post(f'/api/sessions/sessions/{session_id}/confirm/')
        self.assertEqual(confirm.status_code, 200, confirm.data)
        self.assertEqual(
            MentoringSession.objects.get(pk=session_id).status, MentoringSession.Status.CONFIRMED)

    def test_scholar_cannot_confirm_own_booking_request(self):
        slot = AvailabilitySlot.objects.create(
            mentor=self.mentor, start_time=self.start, end_time=self.end, is_booked=False)
        resp = self._client(self.scholar).post('/api/sessions/sessions/', {
            'mentor': self.mentor.id, 'scholar': self.scholar.id, 'slot': slot.id,
            'title': 'Booked by scholar', 'start_time': self.start.isoformat(),
            'end_time': self.end.isoformat(),
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        session_id = resp.data['id']

        confirm = self._client(self.scholar).post(f'/api/sessions/sessions/{session_id}/confirm/')
        self.assertEqual(confirm.status_code, 403, confirm.data)

    def test_legacy_null_created_by_still_confirmable_by_mentor(self):
        session = MentoringSession.objects.create(
            mentor=self.mentor, scholar=self.scholar,
            start_time=self.start, end_time=self.end,
            status=MentoringSession.Status.PENDING, created_by=None,
        )
        resp = self._client(self.mentor).post(f'/api/sessions/sessions/{session.pk}/confirm/')
        self.assertEqual(resp.status_code, 200, resp.data)
        session.refresh_from_db()
        self.assertEqual(session.status, MentoringSession.Status.CONFIRMED)

    def test_legacy_null_created_by_scholar_cannot_confirm(self):
        session = MentoringSession.objects.create(
            mentor=self.mentor, scholar=self.scholar,
            start_time=self.start, end_time=self.end,
            status=MentoringSession.Status.PENDING, created_by=None,
        )
        resp = self._client(self.scholar).post(f'/api/sessions/sessions/{session.pk}/confirm/')
        self.assertEqual(resp.status_code, 403, resp.data)

    def test_cannot_confirm_a_non_pending_session(self):
        propose = self._client(self.mentor).post('/api/sessions/sessions/propose/', {
            'scholar': self.scholar.id,
            'start_time': self.start.isoformat(),
            'end_time': self.end.isoformat(),
            'title': 'Careers chat',
        }, format='json')
        self.assertEqual(propose.status_code, 201, propose.data)
        session_id = propose.data['id']

        cancel = self._client(self.mentor).post(f'/api/sessions/sessions/{session_id}/cancel/')
        self.assertEqual(cancel.status_code, 200, cancel.data)

        confirm = self._client(self.scholar).post(f'/api/sessions/sessions/{session_id}/confirm/')
        self.assertEqual(confirm.status_code, 400, confirm.data)
        session = MentoringSession.objects.get(pk=session_id)
        self.assertEqual(session.status, MentoringSession.Status.CANCELLED)
