from django.contrib import admin
from django.test import TestCase


class EmailLogAdminTests(TestCase):
    def test_registered_readonly_but_deletable(self):
        from apps.notifications.models import EmailLog
        self.assertIn(EmailLog, admin.site._registry)
        ma = admin.site._registry[EmailLog]
        self.assertFalse(ma.has_add_permission(request=None))
        self.assertFalse(ma.has_change_permission(request=None))
        self.assertTrue(ma.has_delete_permission(request=None))
