from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Forum, Thread, Post
from .serializers import ForumSerializer, ThreadSerializer, PostSerializer
from apps.moderation.service import ModerationService


class ForumViewSet(viewsets.ModelViewSet):
    serializer_class = ForumSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['visibility', 'programme', 'is_active']
    search_fields = ['title', 'description']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return Forum.objects.all()
        from django.db.models import Q
        return Forum.objects.filter(
            Q(visibility='open') |
            Q(visibility='programme', programme__cohorts__memberships__user=user) |
            Q(visibility='private', members=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ThreadViewSet(viewsets.ModelViewSet):
    serializer_class = ThreadSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['forum', 'is_pinned', 'is_locked']
    search_fields = ['title']

    def get_queryset(self):
        return Thread.objects.select_related('created_by').order_by('-is_pinned', '-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['thread', 'status']

    def get_queryset(self):
        user = self.request.user
        qs = Post.objects.select_related('author')
        if not (user.is_staff or user.role == 'admin'):
            qs = qs.filter(status=Post.Status.VISIBLE)
        return qs

    def perform_create(self, serializer):
        from apps.messaging.models import Message
        post = serializer.save(author=self.request.user, status=Post.Status.PENDING)
        # Screen forum post via same moderation pipeline
        # Wrap in a temporary Message-like object for shared service
        class _FakeMsg:
            pk = post.pk
            body = post.body
            status = None
            moderation_note = ''
            def save(self, **kwargs): pass

        fake = _FakeMsg()
        result = ModerationService._load_terms() or None
        # Direct term screening
        from apps.moderation.models import BlockedTerm, FlaggedTerm
        import re
        body = post.body.lower()
        blocked = BlockedTerm.objects.filter(is_active=True)
        for bt in blocked:
            if re.search(r'\b' + re.escape(bt.term.lower()) + r'\b', body):
                post.status = Post.Status.HIDDEN
                post.moderation_note = f'Blocked: matched "{bt.term}"'
                post.save(update_fields=['status', 'moderation_note'])
                return
        flagged = FlaggedTerm.objects.filter(is_active=True)
        for ft in flagged:
            if re.search(r'\b' + re.escape(ft.term.lower()) + r'\b', body):
                post.status = Post.Status.FLAGGED
                post.moderation_note = f'Flagged: matched "{ft.term}"'
                post.save(update_fields=['status', 'moderation_note'])
                return
        post.status = Post.Status.VISIBLE
        post.save(update_fields=['status'])
