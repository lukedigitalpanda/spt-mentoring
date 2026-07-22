from django import forms
from django.contrib import admin
from tinymce.widgets import TinyMCE
from .models import NewsItem, PromotionalBanner
from .sanitiser import is_rich_text, sanitise_rich_text

NEWS_AUDIENCE_CHOICES = [
    ('scholar', 'Scholars'),
    ('mentor', 'Mentors'),
    ('sponsor', 'Sponsors'),
]


class NewsItemAdminForm(forms.ModelForm):
    audience_list = forms.MultipleChoiceField(
        choices=NEWS_AUDIENCE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            'Select specific audiences. Leave all unchecked to use the legacy "Audience" dropdown above. '
            'This allows targeting e.g. Scholars + Mentors without Sponsors.'
        ),
    )

    class Meta:
        model = NewsItem
        fields = '__all__'
        widgets = {'body': TinyMCE()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['audience_list'] = self.instance.audience_list or []

    def clean_audience_list(self):
        return list(self.cleaned_data.get('audience_list') or [])

    def clean_body(self):
        # Only sanitise when the body actually looks like HTML - see
        # is_rich_text()'s docstring: running plain text through the
        # sanitiser HTML-escapes bare &/</> characters, mangling ordinary
        # text like "Q&A session".
        body = self.cleaned_data.get('body')
        return sanitise_rich_text(body) if is_rich_text(body) else body


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    form = NewsItemAdminForm
    list_display = ['title', 'status', 'audience_display', 'is_featured', 'published_at', 'author']
    list_filter = ['status', 'audience', 'is_featured', 'programme']
    search_fields = ['title', 'summary', 'body']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'author']
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'summary', 'body', 'cover_image')}),
        ('Publishing', {'fields': ('status', 'is_featured', 'published_at', 'programme')}),
        ('Audience', {
            'description': (
                'Use the multi-select checkboxes to target specific role combinations without including all roles. '
                'If no checkboxes are ticked, the legacy dropdown is used.'
            ),
            'fields': ('audience', 'audience_list'),
        }),
        ('Metadata', {'fields': ('author', 'created_at', 'updated_at')}),
    )

    def audience_display(self, obj):
        if obj.audience_list:
            return ', '.join(obj.audience_list)
        return obj.get_audience_display()
    audience_display.short_description = 'Audience'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(PromotionalBanner)
class PromotionalBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active', 'programme']
    list_filter = ['is_active']
    ordering = ['order']
