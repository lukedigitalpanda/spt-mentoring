from rest_framework import serializers
from .models import Forum, Thread, Post


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'thread', 'author', 'author_name', 'body', 'created_at', 'updated_at', 'status', 'attachment']
        read_only_fields = ['author', 'status', 'created_at', 'updated_at']


class ThreadSerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()
    last_post_at = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = Thread
        fields = ['id', 'forum', 'title', 'created_by', 'created_by_name', 'created_at', 'is_pinned', 'is_locked', 'post_count', 'last_post_at']
        read_only_fields = ['created_by']

    def get_post_count(self, obj):
        return obj.posts.filter(status=Post.Status.VISIBLE).count()

    def get_last_post_at(self, obj):
        last = obj.posts.filter(status=Post.Status.VISIBLE).order_by('-created_at').first()
        return last.created_at if last else None


class ForumSerializer(serializers.ModelSerializer):
    thread_count = serializers.SerializerMethodField()

    class Meta:
        model = Forum
        fields = '__all__'
        read_only_fields = ['created_by']

    def get_thread_count(self, obj):
        return obj.threads.count()
