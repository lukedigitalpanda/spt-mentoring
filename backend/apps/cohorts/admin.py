from django.contrib import admin
from .models import Programme, Cohort, CohortMembership, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fields = ['logo']

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'start_date', 'end_date']
    list_filter = ['is_active']


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ['name', 'programme', 'year', 'is_active']
    list_filter = ['is_active', 'programme']


@admin.register(CohortMembership)
class CohortMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'cohort']
    list_filter = ['cohort']
