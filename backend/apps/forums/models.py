"""
Forum / community discussion – allows communication between Scholars and
Mentors who haven't been directly matched.

Forums can be:
  - Open     – visible to all users (or a programme)
  - Private  – group mentoring, restricted to a cohort or specific members
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Forum(models.Model):
    """A top-level discussion space."""
    class Visibility(models.TextChoices):
        OPEN = 'open', _('Open to all')
        PROGRAMME = 'programme', _('Programme members only')
        PRIVATE = 'private', _('Private group')

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
    """A post within a Thread."""
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending Moderation')
        VISIBLE = 'visible', _('Visible')
        FLAGGED = 'flagged', _('Flagged')
        HIDDEN = 'hidden', _('Hidden')

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='forum_posts')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    moderation_note = models.TextField(blank=True)
    attachment = models.FileField(upload_to='forum_attachments/', blank=True, null=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Post by {self.author.full_name} in "{self.thread.title}"'
