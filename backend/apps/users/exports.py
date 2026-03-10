"""CSV export helpers for User data."""
import csv
from django.http import HttpResponse


class UserCSVExport:
    @classmethod
    def export(cls, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Email', 'First Name', 'Last Name', 'Role', 'Phone',
            'Location', 'Engineering Discipline', 'CRM ID',
            'Is Active', 'Is Verified', 'Date Joined',
        ])

        for user in queryset.iterator():
            writer.writerow([
                user.pk, user.email, user.first_name, user.last_name,
                user.get_role_display(), user.phone, user.location,
                user.engineering_discipline, user.crm_id,
                user.is_active, user.is_verified, user.date_joined,
            ])

        return response
