"""
Forum / community discussion – allows communication between Scholars and
Mentors who haven't been directly matched.

Forums can be:
  - Open     – visible to all users (or a programme)
  - Private  – group mentoring, restricted to a cohort or specific members
"""
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class ForumQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Forums this user is allowed to see (single source of truth for
        forum visibility scoping — used by the API and by N-2 notifications)."""
        if getattr(user, 'is_staff', False) or getattr(user, 'role', None) == 'admin':
            return self
        return self.filter(
            Q(visibility=Forum.Visibility.OPEN) |
            Q(visibility=Forum.Visibility.PROGRAMME, programme__cohorts__memberships__user=user) |
            Q(visibility=Forum.Visibility.PRIVATE, members=user)
        ).distinct()


class Forum(models.Model):
    """A top-level discussion space."""
    class Visibility(models.TextChoices):
        OPEN = 'open', _('Open to all')
        PROGRAMME = 'programme', _('Programme members only')
        PRIVATE = 'private', _('Private group')

    objects = ForumQuerySet.as_manager()

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.OPEN)
    programme = models.ForeignKey(
        'cohorts.Programme', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='forums'
    )
    members = models.ManyToManyField('users.User', related_name='forums', blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='forums_created')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # Notifications for private groups
    notify_all_members = models.BooleanField(default=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.title


class Thread(models.Model):
    """A discussion thread within a Forum."""
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name='threads')
    title = models.CharField(max_length=255)
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='threads_created')
    created_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title


class Post(models.Model):
    """A post within a Thread.

    Post status state machine
    ──────────────────────────
    Forum posts share the same moderation pipeline as direct messages but use
    slightly different status names to reflect their public/thread context:

        PENDING  ──► HIDDEN    (body matched a BlockedTerm — never shown)
                 ──► FLAGGED   (body matched a FlaggedTerm — held for admin review)
                 ──► VISIBLE   (passed all checks — shown to all thread participants)

    Admins can later update FLAGGED or HIDDEN posts back to VISIBLE, or
    permanently set them to HIDDEN.

    Analogy with Message statuses:
        Post.VISIBLE  ≈ Message.DELIVERED
        Post.HIDDEN   ≈ Message.BLOCKED
        Post.FLAGGED  ≈ Message.FLAGGED
        Post.PENDING  ≈ Message.PENDING  (transient — should not persist after screening)
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending Moderation')
        VISIBLE = 'visible', _('Visible')
        FLAGGED = 'flagged', _('Flagged for Review')
        HIDDEN = 'hidden', _('Hidden')

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='forum_posts')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Set only when the author (or staff) edits the post body (Task 13).
    # Unlike updated_at (auto_now), it does NOT change on moderation status
    # flips, so it is the reliable "edited" marker for the UI.
    edited_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    moderation_note = models.TextField(blank=True)
    moderated_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moderated_posts',
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    attachment = models.FileField(upload_to='forum_attachments/', blank=True, null=True)
    # Set once matched mentor(s) have been notified that this post became
    # visible, so edits/re-approvals never re-notify (N-2).
    mentor_notified = models.BooleanField(default=False)
    # Set once earlier thread participants have been notified of this reply
    # becoming visible, so edits/re-approvals never re-notify (P2-3b).
    participants_notified = models.BooleanField(default=False)

    history = HistoricalRecords()

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Post by {self.author.full_name} in "{self.thread.title}"'
