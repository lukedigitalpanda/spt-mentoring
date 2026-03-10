"""
Content moderation & safeguarding.

Maintains lists of blocked and flagged terms.
All incoming messages are screened before delivery.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class BlockedTerm(models.Model):
    """A term that immediately blocks a message from being delivered."""
    term = models.CharField(max_length=200, unique=True)
    added_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, related_name='blocked_terms_added'
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['term']

    def __str__(self):
        return f'[BLOCKED] {self.term}'


class FlaggedTerm(models.Model):
    """A term that holds a message for admin review (does not block immediately)."""
    term = models.CharField(max_length=200, unique=True)
    added_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, related_name='flagged_terms_added'
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    severity = models.PositiveSmallIntegerField(
        default=1, help_text='1=low, 2=medium, 3=high (affects notification priority)'
    )

    class Meta:
        ordering = ['-severity', 'term']

    def __str__(self):
        return f'[FLAGGED:{self.severity}] {self.term}'


class ModerationLog(models.Model):
    """Audit log of every moderation decision."""
    class Action(models.TextChoices):
        BLOCKED = 'blocked', _('Blocked')
        FLAGGED = 'flagged', _('Flagged')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected after review')

    message = models.ForeignKey('messaging.Message', on_delete=models.CASCADE, related_name='moderation_logs')
    action = models.CharField(max_length=20, choices=Action.choices)
    triggered_term = models.CharField(max_length=200, blank=True)
    actioned_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    actioned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-actioned_at']

    def __str__(self):
        return f'Moderation [{self.action}] on Message #{self.message_id}'
