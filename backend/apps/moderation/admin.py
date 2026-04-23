from django.contrib import admin
from .models import BlockedTerm, FlaggedTerm, ModerationLog, ModerationTerm


@admin.register(BlockedTerm)
class BlockedTermAdmin(admin.ModelAdmin):
    list_display = ['term', 'is_active', 'added_at', 'added_by']
    list_filter = ['is_active']
    search_fields = ['term']


@admin.register(FlaggedTerm)
class FlaggedTermAdmin(admin.ModelAdmin):
    list_display = ['term', 'severity', 'is_active', 'added_at', 'added_by']
    list_filter = ['is_active', 'severity']
    search_fields = ['term']


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ['message', 'action', 'triggered_term', 'actioned_by', 'actioned_at']
    list_filter = ['action']
    readonly_fields = ['message', 'action', 'triggered_term', 'actioned_by', 'actioned_at']


@admin.register(ModerationTerm)
class ModerationTermAdmin(admin.ModelAdmin):
    list_display = [
        'term', 'match_type', 'category', 'severity', 'source', 'is_active', 'updated_at',
    ]
    list_filter = ['category', 'severity', 'match_type', 'source', 'is_active']
    search_fields = ['term', 'notes']
    readonly_fields = ['source', 'created_at', 'updated_at']
    list_per_page = 50

    fieldsets = [
        (None, {
            'fields': ['term', 'match_type', 'category', 'severity', 'is_active'],
        }),
        ('Provenance', {
            'fields': ['source', 'notes', 'created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    def get_readonly_fields(self, request, obj=None):
        # Prevent admin users from changing the source on bulk-imported rows,
        # keeping the import/admin distinction clean and auditable.
        if obj and obj.source == 'bulk_import_v1':
            return list(self.readonly_fields) + ['term', 'match_type']
        return self.readonly_fields
