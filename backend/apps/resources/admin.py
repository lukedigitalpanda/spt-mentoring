from django.contrib import admin
from .models import ResourceCategory, Resource, SharedDocument


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'description']
    ordering = ['order', 'name']


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'resource_type', 'audience', 'category', 'is_active', 'download_count', 'created_at']
    list_filter = ['resource_type', 'audience', 'is_active', 'category']
    search_fields = ['title', 'description']
    readonly_fields = ['download_count', 'created_at', 'updated_at', 'uploaded_by']
    fieldsets = (
        (None, {'fields': ('title', 'description', 'resource_type', 'category', 'audience', 'programme', 'is_active')}),
        ('Content', {'fields': ('file', 'url')}),
        ('Metadata', {'fields': ('uploaded_by', 'download_count', 'created_at', 'updated_at')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SharedDocument)
class SharedDocumentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'shared_by', 'shared_with', 'shared_at']
    search_fields = ['filename', 'shared_by__email', 'shared_with__email']
    readonly_fields = ['shared_at']
