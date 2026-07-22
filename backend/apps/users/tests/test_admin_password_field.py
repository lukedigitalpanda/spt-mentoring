"""
Regression test for the Django admin user-edit form password field.

Background (Jun 2026 support incident — Claire Thorpe & Hayleigh McAleese):
the custom ``UserAdminForm`` was a plain ``forms.ModelForm`` with
``fields = '__all__'``. That override stripped Django's special password
handling, so the admin "Password" box rendered as an ordinary editable text
field. Anything an admin typed into it was saved VERBATIM and UNHASHED, which
silently broke login for that user.

The password field on the change form MUST be Django's
``ReadOnlyPasswordHashField`` so raw text cannot be persisted as a password.
Resets are done through the dedicated set-password form instead.

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test apps.users.tests --verbosity=2
"""
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.test import TestCase

from apps.users.admin import UserAdminForm


class AdminPasswordFieldTests(TestCase):
    def test_password_field_is_read_only_hash(self):
        field = UserAdminForm.base_fields.get('password')
        self.assertIsNotNone(field, 'admin form is missing the password field')
        self.assertIsInstance(
            field,
            ReadOnlyPasswordHashField,
            'admin password field must be ReadOnlyPasswordHashField so raw text '
            'typed into the admin Password box cannot be stored unhashed',
        )
