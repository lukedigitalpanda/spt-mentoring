"""
Content moderation & safeguarding.

Maintains lists of blocked and flagged terms.
All incoming messages are screened before delivery.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class ModerationTerm(models.Model):
    """
    Unified bulk-importable moderation term with rich classification.

    Sits alongside the legacy BlockedTerm / FlaggedTerm tables which remain
    untouched for admin-curated entries. The service checks all three tables.

    Severity → runtime action mapping:
      CRITICAL / HIGH  → message blocked  (same outcome as a BlockedTerm hit)
      MEDIUM           → message flagged  (same outcome as a FlaggedTerm hit)
      LOW              → message delivered, ModerationLog entry created (soft warn)

    Substring match note: SUBSTRING terms are matched without word boundaries so
    that obfuscated variants (e.g. sh1t inside "thisissh1ttext") are caught. This
    is intentional — the tradeoff (slightly higher false-positive rate for very
    short terms) is acceptable for a safeguarding platform.
    """

    class MatchType(models.TextChoices):
        EXACT = 'EXACT', _('Exact')
        SUBSTRING = 'SUBSTRING', _('Substring')
        WILDCARD = 'WILDCARD', _('Wildcard')
        REGEX = 'REGEX', _('Regex')
        EMAIL_PATTERN = 'EMAIL_PATTERN', _('Email Pattern')
        URL_FRAGMENT = 'URL_FRAGMENT', _('URL Fragment')
        EMOJI_SINGLE = 'EMOJI_SINGLE', _('Emoji Single')
        EMOJI_COMBO = 'EMOJI_COMBO', _('Emoji Combination')
        EMOJI_OR_SET = 'EMOJI_OR_SET', _('Emoji OR Set')

    class Category(models.TextChoices):
        PROFANITY = 'PROFANITY', _('Profanity')
        SLUR = 'SLUR', _('Slur')
        SEXUAL = 'SEXUAL', _('Sexual')
        VIOLENCE = 'VIOLENCE', _('Violence')
        DRUGS_ALCOHOL = 'DRUGS_ALCOHOL', _('Drugs / Alcohol')
        CONTACT_LEAK = 'CONTACT_LEAK', _('Contact Leak')
        SAFEGUARDING = 'SAFEGUARDING', _('Safeguarding')
        OTHER = 'OTHER', _('Other')

    class Severity(models.TextChoices):
        LOW = 'LOW', _('Low (soft warn)')
        MEDIUM = 'MEDIUM', _('Medium (flag for review)')
        HIGH = 'HIGH', _('High (auto-block)')
        CRITICAL = 'CRITICAL', _('Critical (auto-block + admin alert)')

    term = models.CharField(max_length=500, db_index=True)
    match_type = models.CharField(
        max_length=20, choices=MatchType.choices, default=MatchType.SUBSTRING
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.PROFANITY
    )
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.MEDIUM
    )
    source = models.CharField(
        max_length=100,
        default='bulk_import_v1',
        db_index=True,
        help_text='bulk_import_v1 = importer; admin = manually added via admin UI',
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('term', 'match_type')]
        ordering = ['term']
        verbose_name = 'Moderation Term'
        verbose_name_plural = 'Moderation Terms'

    def __str__(self):
        return f'[{self.severity}:{self.match_type}] {self.term}'


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
