from django import forms
from django.contrib import admin
from .models import ResourceCategory, Resource, SharedDocument


AUDIENCE_CHOICES = [
    ('scholar', 'Scholars'),
    ('mentor', 'Mentors'),
    ('sponsor', 'Sponsors'),
    ('admin', 'Admin only'),
]


class ResourceAdminForm(forms.ModelForm):
    audience_list = forms.MultipleChoiceField(
        choices=AUDIENCE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            'Select specific audiences. Leave all unchecked to fall back to the "Audience" dropdown above. '
            'Selecting audiences here overrides the legacy dropdown and allows precise targeting '
            '(e.g. Scholars + Mentors without Sponsors).'
        ),
    )

    class Meta:
        model = Resource
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['audience_list'] = self.instance.audience_list or []

    def clean_audience_list(self):
        return list(self.cleaned_data.get('audience_list') or [])


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'description']
    ordering = ['order', 'name']


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    form = ResourceAdminForm
    list_display = ['title', 'resource_type', 'audience_display', 'category', 'is_active', 'download_count', 'created_at']
    list_filter = ['resource_type', 'audience', 'is_active', 'category']
    search_fields = ['title', 'description']
    readonly_fields = ['download_count', 'created_at', 'updated_at', 'uploaded_by']
    fieldsets = (
        (None, {'fields': ('title', 'description', 'resource_type', 'category', 'programme', 'is_active')}),
        ('Audience', {
            'description': (
                'Use "Audience (multi-select)" to target specific role combinations. '
                'When blank, the legacy "Audience" dropdown applies.'
            ),
            'fields': ('audience', 'audience_list'),
        }),
        ('Content', {'fields': ('file', 'url')}),
        ('Metadata', {'fields': ('uploaded_by', 'download_count', 'created_at', 'updated_at')}),
    )

    def audience_display(self, obj):
        if obj.audience_list:
            return ', '.join(obj.audience_list)
        return obj.get_audience_display()
    audience_display.short_description = 'Audience'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SharedDocument)
class SharedDocumentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'shared_by', 'shared_with', 'shared_at']
    search_fields = ['filename', 'shared_by__email', 'shared_with__email']
    readonly_fields = ['shared_at']
