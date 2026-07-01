from django.contrib import admin
from django.test import TestCase

class CatalogueAdminTests(TestCase):
    def test_registered_and_read_only(self):
        from apps.notifications.models import EmailCatalogueEntry
        self.assertIn(EmailCatalogueEntry, admin.site._registry)
        ma = admin.site._registry[EmailCatalogueEntry]
        self.assertFalse(ma.has_add_permission(request=None))
        self.assertFalse(ma.has_delete_permission(request=None))
