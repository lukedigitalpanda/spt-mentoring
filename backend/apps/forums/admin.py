from django.contrib import admin
from .models import Forum, Thread, Post


class ThreadInline(admin.TabularInline):
    model = Thread
    extra = 0
    fields = ['title', 'is_pinned', 'is_locked', 'created_by', 'created_at']
    readonly_fields = ['created_by', 'created_at']
    show_change_link = True


@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ['title', 'visibility', 'programme', 'is_active', 'thread_count', 'created_at']
    list_filter = ['visibility', 'is_active', 'programme']
    search_fields = ['title', 'description']
    filter_horizontal = ['members']
    readonly_fields = ['created_at', 'created_by']
    inlines = [ThreadInline]
    fieldsets = (
        (None, {'fields': ('title', 'description', 'is_active')}),
        ('Access', {'fields': ('visibility', 'programme', 'members', 'notify_all_members')}),
        ('Metadata', {'fields': ('created_by', 'created_at')}),
    )

    def thread_count(self, obj):
        return obj.threads.count()
    thread_count.short_description = 'Threads'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class PostInline(admin.TabularInline):
    model = Post
    extra = 0
    fields = ['author', 'body', 'status', 'created_at']
    readonly_fields = ['author', 'created_at']
    show_change_link = True


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ['title', 'forum', 'created_by', 'is_pinned', 'is_locked', 'post_count', 'created_at']
    list_filter = ['is_pinned', 'is_locked', 'forum']
    search_fields = ['title', 'forum__title']
    readonly_fields = ['created_at', 'created_by']
    inlines = [PostInline]

    def post_count(self, obj):
        return obj.posts.count()
    post_count.short_description = 'Posts'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'thread', 'status', 'created_at']
    list_filter = ['status', 'thread__forum']
    search_fields = ['body', 'author__email', 'thread__title']
    readonly_fields = ['author', 'created_at', 'updated_at']
    fields = ['thread', 'author', 'body', 'status', 'moderation_note', 'attachment', 'created_at', 'updated_at']
