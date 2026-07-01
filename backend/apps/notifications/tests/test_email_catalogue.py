from django.test import TestCase

class EmailCatalogueTests(TestCase):
    def test_keys_unique_and_complete(self):
        from apps.notifications.email_catalogue import EMAIL_CATALOGUE
        keys = [e.key for e in EMAIL_CATALOGUE]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), {
            'message', 'scholar_forum_post', 'notification_digest', 'mass_message',
            'no_contact_reminder', 'sponsor_update_reminder', 'moderation_alert', 'password_reset',
        })

    def test_fixed_entries_use_shared_constants(self):
        from apps.notifications.email_catalogue import EMAIL_CATALOGUE
        from apps.messaging.tasks import NO_CONTACT_REMINDER_SUBJECT
        from apps.users.auth_views import PASSWORD_RESET_SUBJECT
        by_key = {e.key: e for e in EMAIL_CATALOGUE}
        self.assertEqual(by_key['no_contact_reminder'].subject, NO_CONTACT_REMINDER_SUBJECT)
        self.assertEqual(by_key['password_reset'].subject, PASSWORD_RESET_SUBJECT)

    def test_infer_category(self):
        from apps.notifications.email_catalogue import infer_category
        self.assertEqual(infer_category('New message from Alice Scholar'), 'message')
        self.assertEqual(infer_category('You have 4 new notifications on SPT Mentoring'), 'notification_digest')
        self.assertEqual(infer_category('Reset your password — Arkwright Mentoring'), 'password_reset')
        self.assertEqual(infer_category('Bob Mentor posted in the forum'), 'scholar_forum_post')
        self.assertEqual(infer_category('Some random admin broadcast'), '')

    def test_infer_category_matches_catalogue_subjects(self):
        """Drift guard: every catalogue subject (except the admin-authored mass
        message) must classify back to its own key, so a future subject-wording
        change can't silently break Email Log categorisation."""
        from apps.notifications.email_catalogue import EMAIL_CATALOGUE, infer_category
        for entry in EMAIL_CATALOGUE:
            if entry.key == 'mass_message':
                continue  # admin-authored subject has no stable pattern
            self.assertEqual(
                infer_category(entry.subject), entry.key,
                f'{entry.key} subject no longer classifies to itself',
            )
