from django.contrib import admin
from .models import NewsItem, PromotionalBanner


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'audience', 'is_featured', 'published_at', 'author']
    list_filter = ['status', 'audience', 'is_featured', 'programme']
    search_fields = ['title', 'summary', 'body']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'author']
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'summary', 'body', 'cover_image')}),
        ('Publishing', {'fields': ('status', 'audience', 'is_featured', 'published_at', 'programme')}),
        ('Metadata', {'fields': ('author', 'created_at', 'updated_at')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(PromotionalBanner)
class PromotionalBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active', 'programme']
    list_filter = ['is_active']
    ordering = ['order']
