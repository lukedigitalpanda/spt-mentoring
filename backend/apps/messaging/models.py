"""
Moderated messaging platform.

All messages pass through the moderation pipeline before delivery:
  1. Blocked-term check  → immediate rejection
  2. Flagged-term check  → held for admin review
  3. Passed              → delivered to recipient
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Conversation(models.Model):
    """A thread between two or more participants."""
    class ConversationType(models.TextChoices):
        DIRECT = 'direct', _('Direct Message')
        GROUP = 'group', _('Group Mentoring')
        SPONSOR_UPDATE = 'sponsor_update', _('Sponsor Update')
        MASS_MESSAGE = 'mass_message', _('Mass Message')

    conversation_type = models.CharField(
        max_length=20, choices=ConversationType.choices, default=ConversationType.DIRECT
    )
    participants = models.ManyToManyField('users.User', related_name='conversations')
    subject = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=True)
    replies_enabled = models.BooleanField(
        default=True,
        help_text='When False, participants cannot reply (used for broadcast-only messages)',
    )

    class SupportStatus(models.TextChoices):
        OPEN = 'open', _('Open')
        IN_PROGRESS = 'in_progress', _('In Progress')
        RESOLVED = 'resolved', _('Resolved')

    support_status = models.CharField(
        max_length=20, choices=SupportStatus.choices, null=True, blank=True,
        help_text='Workflow status for support conversations. Null for non-support threads.',
    )

    # For group mentoring
    cohort = models.ForeignKey(
        'cohorts.Cohort', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='group_conversations'
    )

    def __str__(self):
        return f'Conversation #{self.pk} ({self.get_conversation_type_display()})'

    @property
    def last_message(self):
        # TC-08: exclude messages from inactive users so deactivated accounts
        # do not appear in the left-panel conversation preview.
        return (
            self.messages
            .filter(status=Message.Status.DELIVERED, sender__is_active=True)
            .order_by('-sent_at')
            .first()
        )


class Message(models.Model):
    """A single message within a conversation.

    Message status state machine
    ─────────────────────────────
    Every message starts as PENDING immediately after creation and is
    synchronously screened by ModerationService.screen() before the API
    response is returned.  From there it can only move forward:

        PENDING  ──► BLOCKED   (body matched a BlockedTerm — never delivered)
                 ──► FLAGGED   (body matched a FlaggedTerm — held for admin review)
                 ──► DELIVERED (passed all checks — visible to recipients)

    Admin can later move:
        FLAGGED  ──► DELIVERED  (approved via ModerationService.approve())
                 ──► BLOCKED    (rejected via ModerationService.reject())

    DELETED is a soft-delete applied manually by admins; it hides the message
    from all participants without removing it from the database.

    NOTE: Because screening is synchronous, a message should never remain in
    PENDING state after the API response is returned.  If you observe PENDING
    messages in production it indicates a screening error and should be
    investigated.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending Moderation')
        DELIVERED = 'delivered', _('Delivered')
        FLAGGED = 'flagged', _('Flagged for Review')
        BLOCKED = 'blocked', _('Blocked')
        DELETED = 'deleted', _('Deleted')

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    # Set when the sender edits the message (Task 13). Every edit resets the
    # status to PENDING and re-runs moderation before re-delivery.
    edited_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    moderation_note = models.TextField(blank=True)
    moderated_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moderated_messages'
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    # Attachments
    attachment = models.FileField(upload_to='message_attachments/', blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f'Message from {self.sender.full_name} at {self.sent_at:%Y-%m-%d %H:%M}'


class MessageRead(models.Model):
    """Tracks when a participant has read a message."""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')


class MassMessage(models.Model):
    """Admin-sent broadcast message to a group of users.

    When sent, one Conversation + Message is created per recipient via
    send_mass_message_task().  If replies_enabled=False, each generated
    Conversation will also have replies_enabled=False, and the reply UI
    will be hidden in the front-end for those conversations.

    Replies that ARE enabled go directly back to the sender (the admin
    or Arkwright system account) as a standard direct message.
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SENDING = 'sending', _('Sending')
        SENT = 'sent', _('Sent')

    sender = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='mass_messages_sent')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    recipient_programmes = models.ManyToManyField('cohorts.Programme', blank=True)
    recipient_cohorts = models.ManyToManyField('cohorts.Cohort', blank=True)
    recipient_roles = models.JSONField(default=list, blank=True, help_text='List of role slugs')
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    recipient_count = models.PositiveIntegerField(default=0)
    send_from_email = models.EmailField(default='mentoring@spt.org')
    replies_enabled = models.BooleanField(
        default=True,
        help_text='Allow recipients to reply to this broadcast. When disabled, the reply UI is hidden.',
    )

    def __str__(self):
        return f'Mass message: {self.subject}'


class AbuseReport(models.Model):
    """Report abuse / safeguarding concern."""
    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        UNDER_REVIEW = 'under_review', _('Under Review')
        RESOLVED = 'resolved', _('Resolved')

    reporter = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='abuse_reports_made')
    reported_user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='abuse_reports_received'
    )
    message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True)
    reported_content = models.TextField(
        blank=True,
        help_text='Snapshot of the reported content (message or forum post body) '
                  'taken when the report was filed, so it survives later edits/deletion.',
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    resolved_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='abuse_reports_resolved'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f'Abuse report #{self.pk} by {self.reporter.full_name}'
