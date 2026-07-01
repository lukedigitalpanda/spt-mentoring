from django.core.management import call_command
from django.test import TestCase as _TC

class EmailCatalogueEntryModelTests(_TC):
    def test_can_create_entry(self):
        from apps.notifications.models import EmailCatalogueEntry
        e = EmailCatalogueEntry.objects.create(
            key='k', name='n', trigger='t', recipients='r',
            subject='s', body='b', debounced=False, source='src',
        )
        self.assertEqual(str(e), 'n')


class SyncCommandTests(_TC):
    def test_sync_populates_and_is_idempotent(self):
        from apps.notifications.models import EmailCatalogueEntry
        from apps.notifications.email_catalogue import EMAIL_CATALOGUE
        call_command('sync_email_catalogue')
        self.assertEqual(EmailCatalogueEntry.objects.count(), len(EMAIL_CATALOGUE))
        call_command('sync_email_catalogue')  # again
        self.assertEqual(EmailCatalogueEntry.objects.count(), len(EMAIL_CATALOGUE))

    def test_sync_prunes_stale(self):
        from apps.notifications.models import EmailCatalogueEntry
        EmailCatalogueEntry.objects.create(key='ghost', name='Ghost', trigger='t',
                                            recipients='r', subject='s', body='b')
        call_command('sync_email_catalogue')
        self.assertFalse(EmailCatalogueEntry.objects.filter(key='ghost').exists())

    def test_sync_updates_changed_fields(self):
        from apps.notifications.models import EmailCatalogueEntry
        call_command('sync_email_catalogue')
        EmailCatalogueEntry.objects.filter(key='password_reset').update(subject='WRONG')
        call_command('sync_email_catalogue')
        self.assertNotEqual(
            EmailCatalogueEntry.objects.get(key='password_reset').subject, 'WRONG')
