from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Forum, Thread, Post
from .serializers import ForumSerializer, ThreadSerializer, PostSerializer
from apps.moderation.service import ModerationService


def _alert_staff_for_post(post, triggered_term):
    """Alert admins that a forum post is held for review, reusing the messaging
    moderation helper via a thin proxy so the email/notification format matches."""
    try:
        class _MsgProxy:
            pk = post.pk
            body = post.body
            sender = post.author
            moderation_note = post.moderation_note
        ModerationService._alert_staff(_MsgProxy(), triggered_term)
    except Exception:
        pass


class ForumViewSet(viewsets.ModelViewSet):
    serializer_class = ForumSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['visibility', 'programme', 'is_active']
    search_fields = ['title', 'description']

    def get_queryset(self):
        return Forum.objects.visible_to(self.request.user)

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
        thread = serializer.save(created_by=self.request.user)
        first_post_body = self.request.data.get('first_post', '').strip()
        if not first_post_body:
            return

        post = Post.objects.create(
            thread=thread,
            author=self.request.user,
            body=first_post_body,
            status=Post.Status.PENDING,
        )

        # Run the same moderation pipeline as direct messages so the full term
        # list (profanity, slurs, contact details) applies to forum posts too.
        result = ModerationService.screen_text(post.body)
        if result.status == 'blocked':
            post.status = Post.Status.HIDDEN
        elif result.status == 'flagged':
            post.status = Post.Status.FLAGGED
            _alert_staff_for_post(post, result.triggered_term)
        else:
            post.status = Post.Status.VISIBLE
        post.moderation_note = result.note
        post.save(update_fields=['status', 'moderation_note'])

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['thread', 'status']
    # P2-4: PUT is not supported - edits go through PATCH (partial_update
    # below) so they are always re-moderated. DELETE stays admin-only, see
    # get_permissions (mirroring ThreadViewSet's convention).
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Post.objects.select_related('author')
        if not (user.is_staff or user.role == 'admin'):
            qs = qs.filter(status=Post.Status.VISIBLE)
        return qs

    def create(self, request, *args, **kwargs):
        """
        Override create() to return a meaningful HTTP status and message for
        each moderation outcome:

          201 Created     – post visible immediately (passed all checks)
          202 Accepted    – post held for review (flagged term or contact detail)
          400 Bad Request – post matched a blocked term; permanently hidden

        Forum posts run through the same ModerationService pipeline as direct
        messages so the full flagged-terms list (profanity, slurs, contact
        details) applies consistently (FOR-03/04/05).  The post is saved in all
        cases so admins have a full audit trail.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user, status=Post.Status.PENDING)

        result = ModerationService.screen_text(post.body)
        return self._apply_moderation_outcome(post, result, serializer=serializer)

    def _apply_moderation_outcome(self, post, result, serializer=None):
        """Shared moderation status mapping + response envelopes for create()
        and partial_update().

        Applies the screening outcome to the post (HIDDEN / FLAGGED / VISIBLE)
        and returns the matching Response: 400 blocked, 202 held for review,
        or - when the post is visible - 201 with headers (create, serializer
        given) / 200 (edit)."""
        if result.status == 'blocked':
            post.status = Post.Status.HIDDEN
            post.moderation_note = result.note
            post.save(update_fields=['status', 'moderation_note'])
            return Response(
                {
                    'detail': (
                        'Your post could not be submitted as it contains restricted content. '
                        'If you believe this is an error please contact support.'
                    ),
                    'moderation_status': 'blocked',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if result.status == 'flagged':
            post.status = Post.Status.FLAGGED
            post.moderation_note = result.note
            post.save(update_fields=['status', 'moderation_note'])
            _alert_staff_for_post(post, result.triggered_term)
            return Response(
                {
                    'detail': (
                        'Your post has been submitted and is awaiting review '
                        'before it becomes visible. You will be notified once approved.'
                    ),
                    'moderation_status': 'pending_review',
                },
                status=status.HTTP_202_ACCEPTED,
            )

        # Passed all checks — make visible
        post.status = Post.Status.VISIBLE
        post.moderation_note = result.note
        post.save(update_fields=['status', 'moderation_note'])
        if serializer is not None:
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(self.get_serializer(post).data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        """P2-4: author-or-staff post editing with mandatory re-moderation.

        Every edit resets the post to PENDING, sets edited_at (the reliable
        "edited" marker - updated_at also moves on moderation status flips)
        and re-runs the same screening pipeline as create()."""
        post = self.get_object()
        user = request.user

        if post.author_id != user.id and not (user.is_staff or user.role == 'admin'):
            return Response(
                {'detail': 'You can only edit your own posts.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        body = request.data.get('body') or ''
        if not isinstance(body, str) or not body.strip():
            return Response(
                {'detail': 'Post body cannot be empty.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        post.body = body.strip()
        post.edited_at = timezone.now()
        post.status = Post.Status.PENDING
        post.save(update_fields=['body', 'edited_at', 'status'])

        result = ModerationService.screen_text(post.body)
        return self._apply_moderation_outcome(post, result)
