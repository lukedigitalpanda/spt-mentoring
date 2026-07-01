from django.test import TestCase

class EmailCatalogueEntryModelTests(TestCase):
    def test_can_create_entry(self):
        from apps.notifications.models import EmailCatalogueEntry
        e = EmailCatalogueEntry.objects.create(
            key='k', name='n', trigger='t', recipients='r',
            subject='s', body='b', debounced=False, source='src',
        )
        self.assertEqual(str(e), 'n')
