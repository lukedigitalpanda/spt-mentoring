"""
Moderation service – screens message bodies for blocked/flagged terms.

Usage:
    from apps.moderation.service import ModerationService
    result = ModerationService.screen(message)
"""
import re
import logging
from django.utils import timezone
from .models import BlockedTerm, FlaggedTerm, ModerationLog

logger = logging.getLogger('apps.moderation')


class ModerationResult:
    def __init__(self, status, triggered_term=''):
        self.status = status          # 'delivered' | 'flagged' | 'blocked'
        self.triggered_term = triggered_term


class ModerationService:
    _blocked_terms_cache = None
    _flagged_terms_cache = None

    @classmethod
    def _load_terms(cls):
        cls._blocked_terms_cache = list(
            BlockedTerm.objects.filter(is_active=True).values_list('term', flat=True)
        )
        cls._flagged_terms_cache = list(
            FlaggedTerm.objects.filter(is_active=True).values_list('term', flat=True)
        )

    @classmethod
    def _contains_term(cls, text: str, terms: list) -> str:
        """Returns the first matched term or empty string."""
        normalized = text.lower()
        for term in terms:
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            if re.search(pattern, normalized):
                return term
        return ''

    @classmethod
    def screen(cls, message) -> ModerationResult:
        """
        Screen a Message instance.
        Updates the message status and creates a ModerationLog entry.
        Returns a ModerationResult.
        """
        from apps.messaging.models import Message

        cls._load_terms()
        body = message.body

        # 1. Check blocked terms
        blocked_hit = cls._contains_term(body, cls._blocked_terms_cache)
        if blocked_hit:
            message.status = Message.Status.BLOCKED
            message.moderation_note = f'Blocked: matched term "{blocked_hit}"'
            message.save(update_fields=['status', 'moderation_note'])
            ModerationLog.objects.create(
                message=message,
                action=ModerationLog.Action.BLOCKED,
                triggered_term=blocked_hit,
            )
            logger.warning('Message #%d blocked – term: %s', message.pk, blocked_hit)
            return ModerationResult('blocked', blocked_hit)

        # 2. Check flagged terms
        flagged_hit = cls._contains_term(body, cls._flagged_terms_cache)
        if flagged_hit:
            message.status = Message.Status.FLAGGED
            message.moderation_note = f'Flagged: matched term "{flagged_hit}"'
            message.save(update_fields=['status', 'moderation_note'])
            ModerationLog.objects.create(
                message=message,
                action=ModerationLog.Action.FLAGGED,
                triggered_term=flagged_hit,
            )
            logger.warning('Message #%d flagged – term: %s', message.pk, flagged_hit)
            return ModerationResult('flagged', flagged_hit)

        # 3. Passed – deliver
        message.status = Message.Status.DELIVERED
        message.save(update_fields=['status'])
        return ModerationResult('delivered')

    @classmethod
    def approve(cls, message, admin_user, notes=''):
        """Admin approves a flagged message."""
        from apps.messaging.models import Message
        message.status = Message.Status.DELIVERED
        message.moderated_by = admin_user
        message.moderated_at = timezone.now()
        message.moderation_note = notes or 'Approved by admin'
        message.save(update_fields=['status', 'moderated_by', 'moderated_at', 'moderation_note'])
        ModerationLog.objects.create(
            message=message,
            action=ModerationLog.Action.APPROVED,
            actioned_by=admin_user,
            notes=notes,
        )

    @classmethod
    def reject(cls, message, admin_user, notes=''):
        """Admin rejects a flagged message."""
        from apps.messaging.models import Message
        message.status = Message.Status.BLOCKED
        message.moderated_by = admin_user
        message.moderated_at = timezone.now()
        message.moderation_note = notes or 'Rejected by admin'
        message.save(update_fields=['status', 'moderated_by', 'moderated_at', 'moderation_note'])
        ModerationLog.objects.create(
            message=message,
            action=ModerationLog.Action.REJECTED,
            actioned_by=admin_user,
            notes=notes,
        )
