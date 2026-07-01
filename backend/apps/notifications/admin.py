from django.contrib import admin
from .models import Notification, EmailCatalogueEntry, EmailLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['user__email', 'title', 'body']
    ordering = ['-created_at']


@admin.register(EmailCatalogueEntry)
class EmailCatalogueEntryAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'recipients', 'debounced')
    list_filter = ('debounced',)
    search_fields = ('name', 'key', 'subject', 'body')
    readonly_fields = ('key', 'name', 'trigger', 'recipients', 'subject', 'body',
                       'debounced', 'source', 'notes', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # view-only detail page

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'to', 'subject', 'category', 'status')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('to', 'subject')
    readonly_fields = ('to', 'from_email', 'subject', 'body', 'status', 'error',
                       'category', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True
