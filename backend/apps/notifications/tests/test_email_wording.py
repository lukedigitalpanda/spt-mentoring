from django.test import TestCase


class FixedEmailBuildersTests(TestCase):
    def test_no_contact_builder(self):
        from apps.messaging.tasks import NO_CONTACT_REMINDER_SUBJECT, build_no_contact_body
        self.assertEqual(NO_CONTACT_REMINDER_SUBJECT, 'SPT Mentoring – Time to connect!')
        body = build_no_contact_body('Sam')
        self.assertIn('Hi Sam,', body)
        self.assertIn("haven't been in touch recently", body)

    def test_sponsor_builder(self):
        from apps.messaging.tasks import SPONSOR_UPDATE_SUBJECT, build_sponsor_update_body
        self.assertEqual(SPONSOR_UPDATE_SUBJECT, 'SPT Scholarships – Time to update your sponsor')
        body = build_sponsor_update_body('Sam', 'Acme Trust')
        self.assertIn('Hi Sam,', body)
        self.assertIn('Acme Trust', body)

    def test_moderation_alert_builder(self):
        from apps.moderation.service import build_moderation_alert
        subject, body = build_moderation_alert('Al Ice', 'al@x.com', 'badword',
                                               'https://x/admin/msg/5/', 5)
        self.assertEqual(subject, '[SPT Moderation] Flagged message requires review (#5)')
        self.assertIn('Al Ice (al@x.com)', body)
        self.assertIn('badword', body)

    def test_password_reset_builder(self):
        from apps.users.auth_views import PASSWORD_RESET_SUBJECT, build_password_reset_body
        self.assertEqual(PASSWORD_RESET_SUBJECT, 'Reset your password — Arkwright Mentoring')
        body = build_password_reset_body('Sam', 'https://x/reset-password/u/t')
        self.assertIn('Hi Sam,', body)
        self.assertIn('https://x/reset-password/u/t', body)
        self.assertIn('valid for 3 days', body)
