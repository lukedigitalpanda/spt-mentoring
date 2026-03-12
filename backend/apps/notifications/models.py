"""
In-app notification model for SPT Mentoring Platform.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Type(models.TextChoices):
        SESSION_REQUEST   = 'session_request',   _('Session Request')
        SESSION_CONFIRMED = 'session_confirmed',  _('Session Confirmed')
        SESSION_CANCELLED = 'session_cancelled',  _('Session Cancelled')
        SESSION_REMINDER  = 'session_reminder',   _('Session Reminder')
        SESSION_FEEDBACK  = 'session_feedback',   _('Feedback Requested')
        MESSAGE           = 'message',             _('New Message')
        MATCH             = 'match',               _('New Match')
        FORUM_REPLY       = 'forum_reply',         _('Forum Reply')
        SURVEY            = 'survey',              _('New Survey')
        GOAL              = 'goal',                _('Goal Update')
        SYSTEM            = 'system',              _('System')

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500)
    link = models.CharField(max_length=200, blank=True, help_text='Frontend URL to navigate to')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'

    def __str__(self):
        return f"[{self.notification_type}] {self.title} → {self.user.full_name}"
