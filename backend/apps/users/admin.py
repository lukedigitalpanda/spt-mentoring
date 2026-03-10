from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin
from .models import User, MentorProfile, ScholarProfile, SponsorProfile, MentoringMatch


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, BaseUserAdmin):
    list_display = ['email', 'full_name', 'role', 'is_active', 'is_verified', 'date_joined']
    list_filter = ['role', 'is_active', 'is_verified']
    search_fields = ['email', 'first_name', 'last_name', 'crm_id']
    ordering = ['last_name', 'first_name']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Profile', {'fields': ('role', 'phone', 'bio', 'profile_picture', 'date_of_birth', 'location', 'engineering_discipline', 'interests')}),
        ('Safeguarding', {'fields': ('is_verified', 'safeguarding_training_date')}),
        ('CRM', {'fields': ('crm_id',)}),
        ('Notifications', {'fields': ('notification_email', 'notification_sms')}),
    )


@admin.register(MentoringMatch)
class MentoringMatchAdmin(admin.ModelAdmin):
    list_display = ['scholar', 'mentor', 'is_active', 'matched_on']
    list_filter = ['is_active']
    search_fields = ['scholar__email', 'mentor__email']


admin.site.register(MentorProfile)
admin.site.register(ScholarProfile)
admin.site.register(SponsorProfile)
