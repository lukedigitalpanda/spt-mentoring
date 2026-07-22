import csv
import io

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
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


_EMOJI_MATCH_TYPES = {
    ModerationTerm.MatchType.EMOJI_SINGLE,
    ModerationTerm.MatchType.EMOJI_COMBO,
    ModerationTerm.MatchType.EMOJI_OR_SET,
}

_SCORING_HELP = (
    'Emoji moderation uses a risk score rather than a simple block/allow decision. '
    'Single emojis produce a low score (5–30) and are never auto-blocked — '
    'they are allowed through with an audit log entry or a review-queue flag. '
    'Combination rules (EMOJI_COMBO) require all emojis to appear within '
    'a proximity window and score higher (50–80). '
    'This prevents high false-positive rates from common individual emojis. '
    'Score ≥ 80 → blocked; 50–79 → held for review; 20–49 → delivered + review queue; '
    '< 20 → delivered + audit log. '
    'Ambiguous COMBO rows (marked in import log) may need to be changed to '
    'EMOJI_OR_SET if the emojis are independent code words rather than a gesture combo.'
)


@admin.register(ModerationTerm)
class ModerationTermAdmin(admin.ModelAdmin):
    list_display = [
        'term_display', 'match_type', 'category', 'severity', 'source', 'is_active', 'updated_at',
    ]
    list_filter = ['category', 'severity', 'match_type', 'source', 'is_active']
    search_fields = ['term', 'notes']
    readonly_fields = ['source', 'created_at', 'updated_at']
    list_per_page = 50
    actions = ['export_emoji_rules_csv']

    fieldsets = [
        (None, {
            'fields': ['term', 'match_type', 'category', 'severity', 'is_active'],
        }),
        ('Provenance', {
            'fields': ['source', 'notes', 'created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request)

    @admin.display(description='Pattern')
    def term_display(self, obj):
        """Render emoji patterns in a monospace span wide enough for multi-emoji sequences."""
        if obj.match_type in _EMOJI_MATCH_TYPES:
            return format_html(
                '<span style="font-family:monospace;font-size:1.4em;letter-spacing:2px">{}</span>',
                obj.term,
            )
        return obj.term

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.source == 'bulk_import_v1':
            return list(self.readonly_fields) + ['term', 'match_type']
        return self.readonly_fields

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['emoji_scoring_help'] = _SCORING_HELP
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description='Export selected emoji rules to CSV')
    def export_emoji_rules_csv(self, request, queryset):
        """Download the currently active emoji ruleset as a CSV for safeguarding review."""
        emoji_qs = queryset.filter(
            match_type__in=list(_EMOJI_MATCH_TYPES),
            is_active=True,
        )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['term', 'match_type', 'category', 'severity', 'source', 'notes', 'updated_at'])
        for row in emoji_qs.order_by('match_type', 'term'):
            writer.writerow([
                row.term, row.match_type, row.category,
                row.severity, row.source, row.notes, row.updated_at,
            ])
        response = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="emoji_moderation_rules.csv"'
        return response
