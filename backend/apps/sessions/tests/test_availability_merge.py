from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from apps.users.models import User
from apps.sessions.models import AvailabilitySlot


class AvailabilitySlotMergeTest(TestCase):
    """Overlapping/touching unbooked slots for the same mentor should merge on creation."""

    def setUp(self):
        self.mentor = User.objects.create_user(
            username='mentor', email='m@example.com', password='x',
            first_name='Mary', last_name='Mentor', role='mentor')
        self.other_mentor = User.objects.create_user(
            username='mentor2', email='m2@example.com', password='x',
            first_name='Mo', last_name='Mentor', role='mentor')
        self.now = timezone.now().replace(microsecond=0) + timedelta(days=1)
        self.url = '/api/sessions/slots/'

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def _create(self, user, start, end, notes=''):
        return self._client(user).post(self.url, {
            'start_time': start.isoformat(),
            'end_time': end.isoformat(),
            'notes': notes,
        }, format='json')

    def test_overlapping_unbooked_slots_merge_to_one_spanning_slot(self):
        AvailabilitySlot.objects.create(
            mentor=self.mentor, is_booked=False,
            start_time=self.now + timedelta(minutes=30),
            end_time=self.now + timedelta(minutes=90),
        )
        resp = self._create(
            self.mentor, self.now, self.now + timedelta(minutes=60))
        self.assertEqual(resp.status_code, 201)

        slots = AvailabilitySlot.objects.filter(mentor=self.mentor)
        self.assertEqual(slots.count(), 1)
        merged = slots.first()
        self.assertEqual(merged.start_time, self.now)
        self.assertEqual(merged.end_time, self.now + timedelta(minutes=90))
        # Response reflects the merged extent.
        self.assertEqual(parse_datetime(resp.data['start_time']), merged.start_time)
        self.assertEqual(parse_datetime(resp.data['end_time']), merged.end_time)

    def test_exact_touching_slots_merge(self):
        AvailabilitySlot.objects.create(
            mentor=self.mentor, is_booked=False,
            start_time=self.now + timedelta(hours=1),
            end_time=self.now + timedelta(hours=2),
        )
        resp = self._create(
            self.mentor, self.now, self.now + timedelta(hours=1))
        self.assertEqual(resp.status_code, 201)

        slots = AvailabilitySlot.objects.filter(mentor=self.mentor)
        self.assertEqual(slots.count(), 1)
        merged = slots.first()
        self.assertEqual(merged.start_time, self.now)
        self.assertEqual(merged.end_time, self.now + timedelta(hours=2))

    def test_booked_slots_are_never_merged(self):
        booked = AvailabilitySlot.objects.create(
            mentor=self.mentor, is_booked=True,
            start_time=self.now + timedelta(minutes=30),
            end_time=self.now + timedelta(minutes=90),
        )
        resp = self._create(
            self.mentor, self.now, self.now + timedelta(minutes=60))
        self.assertEqual(resp.status_code, 201)

        slots = AvailabilitySlot.objects.filter(mentor=self.mentor)
        self.assertEqual(slots.count(), 2)
        booked.refresh_from_db()
        self.assertEqual(booked.start_time, self.now + timedelta(minutes=30))
        self.assertEqual(booked.end_time, self.now + timedelta(minutes=90))

    def test_disjoint_slots_are_untouched(self):
        AvailabilitySlot.objects.create(
            mentor=self.mentor, is_booked=False,
            start_time=self.now + timedelta(hours=3),
            end_time=self.now + timedelta(hours=4),
        )
        resp = self._create(
            self.mentor, self.now, self.now + timedelta(hours=1))
        self.assertEqual(resp.status_code, 201)

        slots = AvailabilitySlot.objects.filter(mentor=self.mentor).order_by('start_time')
        self.assertEqual(slots.count(), 2)
        self.assertEqual(slots[0].start_time, self.now)
        self.assertEqual(slots[0].end_time, self.now + timedelta(hours=1))

    def test_only_merges_slots_belonging_to_same_mentor(self):
        AvailabilitySlot.objects.create(
            mentor=self.other_mentor, is_booked=False,
            start_time=self.now + timedelta(minutes=30),
            end_time=self.now + timedelta(minutes=90),
        )
        resp = self._create(
            self.mentor, self.now, self.now + timedelta(minutes=60))
        self.assertEqual(resp.status_code, 201)

        self.assertEqual(AvailabilitySlot.objects.filter(mentor=self.mentor).count(), 1)
        self.assertEqual(AvailabilitySlot.objects.filter(mentor=self.other_mentor).count(), 1)

    def test_merges_across_more_than_two_slots_in_one_pass(self):
        # Two pre-existing slots that do NOT overlap each other, but the
        # newly created slot spans and touches both -> all three collapse
        # into a single slot in one perform_create pass.
        AvailabilitySlot.objects.create(
            mentor=self.mentor, is_booked=False,
            start_time=self.now + timedelta(minutes=30),
            end_time=self.now + timedelta(minutes=60),
        )
        AvailabilitySlot.objects.create(
            mentor=self.mentor, is_booked=False,
            start_time=self.now + timedelta(minutes=90),
            end_time=self.now + timedelta(minutes=120),
        )
        resp = self._create(
            self.mentor, self.now, self.now + timedelta(minutes=100))
        self.assertEqual(resp.status_code, 201)

        slots = AvailabilitySlot.objects.filter(mentor=self.mentor)
        self.assertEqual(slots.count(), 1)
        merged = slots.first()
        self.assertEqual(merged.start_time, self.now)
        self.assertEqual(merged.end_time, self.now + timedelta(minutes=120))
