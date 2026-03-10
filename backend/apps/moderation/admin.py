from django.contrib import admin
from .models import BlockedTerm, FlaggedTerm, ModerationLog


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
