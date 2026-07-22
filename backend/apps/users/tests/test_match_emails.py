"""
Tests for P2-3(a): email both parties, with names and a direct link, when a
mentoring match is made (created or reinstated).

Run with:
    docker compose exec -T backend python manage.py test apps.users apps.notifications -v 1
"""
from django.core import mail
from django.test import TestCase, override_settings

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
        notification_email=True,
    )
    defaults.update(kwargs)
    return User.objects.create(**defaults)


@override_settings(
    FRONTEND_URL='https://mentoring.example.test',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class MatchEmailTests(TestCase):

    def setUp(self):
        self.scholar = make_user(
            'scholar@example.com', User.Role.SCHOLAR,
            first_name='Sam', last_name='Scholar',
        )
        self.mentor = make_user(
            'mentor@example.com', User.Role.MENTOR,
            first_name='Mo', last_name='Mentor',
        )

    def test_match_creation_sends_named_emails_to_both_parties(self):
        mail.outbox = []

        MentoringMatch.objects.create(scholar=self.scholar, mentor=self.mentor, is_active=True)

        self.assertEqual(len(mail.outbox), 2)

        to_scholar = next(m for m in mail.outbox if m.to == [self.scholar.email])
        to_mentor = next(m for m in mail.outbox if m.to == [self.mentor.email])

        self.assertEqual(to_scholar.subject, 'SPT Mentoring - You have been matched')
        self.assertIn('Sam', to_scholar.body)
        self.assertIn('Mo Mentor', to_scholar.body)
        self.assertIn('mentor', to_scholar.body)
        self.assertIn('https://mentoring.example.test/messages', to_scholar.body)

        self.assertEqual(to_mentor.subject, 'SPT Mentoring - You have been matched')
        self.assertIn('Mo', to_mentor.body)
        self.assertIn('Sam Scholar', to_mentor.body)
        self.assertIn('scholar', to_mentor.body)
        self.assertIn('https://mentoring.example.test/messages', to_mentor.body)

    def test_match_email_respects_notification_preference(self):
        self.scholar.notification_email = False
        self.scholar.save(update_fields=['notification_email'])
        mail.outbox = []

        MentoringMatch.objects.create(scholar=self.scholar, mentor=self.mentor, is_active=True)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.mentor.email])

    def test_reinstatement_sends_named_emails_to_both_parties(self):
        match = MentoringMatch.objects.create(scholar=self.scholar, mentor=self.mentor, is_active=True)
        match.is_active = False
        match.save(update_fields=['is_active'])
        mail.outbox = []

        match.is_active = True
        match.save(update_fields=['is_active'])

        self.assertEqual(len(mail.outbox), 2)

    def test_deactivation_sends_no_email(self):
        match = MentoringMatch.objects.create(scholar=self.scholar, mentor=self.mentor, is_active=True)
        mail.outbox = []

        match.is_active = False
        match.save(update_fields=['is_active'])

        self.assertEqual(len(mail.outbox), 0)

    def test_unrelated_field_update_on_active_match_sends_no_email_or_notification(self):
        from apps.notifications.models import Notification

        match = MentoringMatch.objects.create(scholar=self.scholar, mentor=self.mentor, is_active=True)
        mail.outbox = []
        notes_before = Notification.objects.filter(
            user__in=[self.scholar, self.mentor], notification_type=Notification.Type.MATCH,
        ).count()

        match.notes = 'reviewed by admin'
        match.save(update_fields=['notes'])

        self.assertEqual(len(mail.outbox), 0)
        notes_after = Notification.objects.filter(
            user__in=[self.scholar, self.mentor], notification_type=Notification.Type.MATCH,
        ).count()
        self.assertEqual(notes_after, notes_before)

    def test_genuine_reinstatement_false_to_true_sends_emails_once(self):
        match = MentoringMatch.objects.create(scholar=self.scholar, mentor=self.mentor, is_active=True)
        match.is_active = False
        match.save(update_fields=['is_active'])
        mail.outbox = []

        match.is_active = True
        match.save(update_fields=['is_active'])

        self.assertEqual(len(mail.outbox), 2)
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, sorted([self.scholar.email, self.mentor.email]))
