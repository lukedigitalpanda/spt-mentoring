from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.users.models import User
from apps.sessions.models import MentoringSession


class SessionModelHelpersTest(TestCase):
    def setUp(self):
        self.mentor = User.objects.create_user(
            username='mentor', email='m@example.com', password='x', first_name='Mary', last_name='Mentor', role='mentor')
        self.scholar = User.objects.create_user(
            username='scholar', email='s@example.com', password='x', first_name='Sam', last_name='Scholar', role='scholar')

    def _session(self, start, end, status=MentoringSession.Status.CONFIRMED):
        return MentoringSession.objects.create(
            mentor=self.mentor, scholar=self.scholar,
            start_time=start, end_time=end, status=status)

    def test_room_name_is_stable_and_prefixed(self):
        now = timezone.now()
        s = self._session(now, now + timedelta(hours=1))
        self.assertTrue(s.room_name.startswith('SPTMentoring-'))
        # Stable across reloads from the DB.
        self.assertEqual(s.room_name, MentoringSession.objects.get(pk=s.pk).room_name)

    def test_is_joinable_true_within_window(self):
        now = timezone.now()
        s = self._session(now - timedelta(minutes=1), now + timedelta(minutes=59))
        self.assertTrue(s.is_joinable)

    def test_is_joinable_false_when_too_early(self):
        now = timezone.now()
        s = self._session(now + timedelta(hours=1), now + timedelta(hours=2))
        self.assertFalse(s.is_joinable)

    def test_is_joinable_false_when_not_confirmed(self):
        now = timezone.now()
        s = self._session(now - timedelta(minutes=1), now + timedelta(minutes=59),
                          status=MentoringSession.Status.PENDING)
        self.assertFalse(s.is_joinable)
