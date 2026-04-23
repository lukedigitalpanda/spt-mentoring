"""
Moderation service – screens message bodies for blocked/flagged terms.

Usage:
    from apps.moderation.service import ModerationService
    result = ModerationService.screen(message)

State machine overview
──────────────────────
Every Message (and forum Post) passes through this pipeline synchronously at
creation time.  There are two distinct hold states that serve different purposes:

┌──────────────────────────────────────────────────────────────────────────────┐
│  State              │  Triggered by          │  Visible to sender?          │
├──────────────────────────────────────────────────────────────────────────────┤
│  PENDING            │  Initial default state │  Transient — not persisted   │
│                     │  before screening      │  after screen() returns      │
├──────────────────────────────────────────────────────────────────────────────┤
│  BLOCKED            │  Body contains a term  │  Yes — sender receives a     │
│                     │  from BlockedTerm table│  400 Bad Request response     │
│                     │  (e.g. hate speech,    │  with a clear rejection msg  │
│                     │  personal identifiers) │                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  FLAGGED            │  Body contains a term  │  Yes — sender receives a     │
│  (= held for review)│  from FlaggedTerm table│  202 Accepted response with  │
│                     │  (e.g. safeguarding    │  "awaiting review" message   │
│                     │  keywords, red-flag    │  Admins are alerted via email│
│                     │  phrases)              │  + in-app notification       │
├──────────────────────────────────────────────────────────────────────────────┤
│  DELIVERED          │  Passed both checks    │  Normal delivery — visible   │
│  (Messages) /       │                        │  to all conversation         │
│  VISIBLE (Posts)    │                        │  participants                │
└──────────────────────────────────────────────────────────────────────────────┘

Admin resolution paths:
  FLAGGED → DELIVERED  via ModerationService.approve()  (message is safe)
  FLAGGED → BLOCKED    via ModerationService.reject()   (message is harmful)

Both BlockedTerm and FlaggedTerm lists are managed in the Django admin under
the Moderation section and are reloaded fresh on every screen() call.

ModerationTerm extension
────────────────────────
The service also checks the ModerationTerm table, which is populated by the
import_moderation_terms management command.  Severity maps to action:

  CRITICAL / HIGH  → blocked  (same outcome as a BlockedTerm hit)
  MEDIUM           → flagged  (same outcome as a FlaggedTerm hit)
  LOW              → delivered, ModerationLog entry written (soft warn only)

ModerationTerm patterns (regex, wildcard, email, etc.) are compiled once and
cached at the class level.  Call ModerationService.invalidate_cache() to force
a rebuild — the import command does this automatically after each run.
"""
import re
import logging
from django.db import models
from django.utils import timezone
from .models import BlockedTerm, FlaggedTerm, ModerationLog, ModerationTerm

logger = logging.getLogger('apps.moderation')


def _email_glob_to_regex(term: str) -> re.Pattern:
    """
    Convert an email-style glob term to a compiled regex.

    '*@hotmail.com'  →  [\\w.+-]+@hotmail\\.com
    '*@*'            →  general email shape
    '@'              →  general email shape
    '@gmail.com'     →  r'[\w.+-]+@gmail\.com'
    """
    generic_email = re.compile(r'[\w.+\-]+@[\w.\-]+\.[a-z]{2,}', re.IGNORECASE)

    if term in ('@', '*@*'):
        return generic_email

    # '*@domain.tld' or '@domain.tld'
    if term.startswith('*@') or term.startswith('@'):
        domain_part = term.lstrip('*').lstrip('@')
        if domain_part:
            return re.compile(r'[\w.+\-]+@' + re.escape(domain_part), re.IGNORECASE)
        return generic_email

    # Fallback — treat literal @ as generic email shape
    return generic_email


def _compile_term_pattern(term: str, match_type: str) -> re.Pattern | None:
    """Compile and return a regex Pattern for the given term and match_type."""
    try:
        if match_type == ModerationTerm.MatchType.EXACT:
            return re.compile(r'(?i)\b' + re.escape(term) + r'\b')
        elif match_type == ModerationTerm.MatchType.SUBSTRING:
            return re.compile(re.escape(term), re.IGNORECASE)
        elif match_type == ModerationTerm.MatchType.WILDCARD:
            # Replace * with .* (escape everything else first)
            escaped = re.escape(term).replace(r'\*', '.*')
            return re.compile(escaped, re.IGNORECASE)
        elif match_type == ModerationTerm.MatchType.REGEX:
            return re.compile(term, re.IGNORECASE)
        elif match_type == ModerationTerm.MatchType.EMAIL_PATTERN:
            return _email_glob_to_regex(term)
        elif match_type == ModerationTerm.MatchType.URL_FRAGMENT:
            return re.compile(re.escape(term), re.IGNORECASE)
    except re.error:
        logger.warning('ModerationTerm: invalid pattern skipped — term=%r match_type=%s', term, match_type)
    return None


class ModerationResult:
    def __init__(self, status, triggered_term=''):
        self.status = status          # 'delivered' | 'flagged' | 'blocked'
        self.triggered_term = triggered_term


class ModerationService:
    # Legacy term caches — reloaded fresh on every screen() call.
    _blocked_terms_cache = None
    _flagged_terms_cache = None

    # Compiled ModerationTerm pattern cache — built once, invalidated explicitly.
    # Each list holds (compiled_pattern, term_str) tuples.
    _mt_block_patterns: list | None = None   # CRITICAL + HIGH → block
    _mt_flag_patterns: list | None = None    # MEDIUM → flag
    _mt_low_patterns: list | None = None     # LOW → deliver + log

    @classmethod
    def invalidate_cache(cls):
        """Force the next screen() call to rebuild all caches from the database."""
        cls._blocked_terms_cache = None
        cls._flagged_terms_cache = None
        cls._mt_block_patterns = None
        cls._mt_flag_patterns = None
        cls._mt_low_patterns = None

    @classmethod
    def _load_terms(cls):
        """Reload legacy BlockedTerm / FlaggedTerm lists (called on every screen())."""
        cls._blocked_terms_cache = list(
            BlockedTerm.objects.filter(is_active=True).values_list('term', flat=True)
        )
        cls._flagged_terms_cache = list(
            FlaggedTerm.objects.filter(is_active=True).values_list('term', flat=True)
        )

    @classmethod
    def _ensure_moderation_term_patterns(cls):
        """Build compiled ModerationTerm pattern lists if not already cached."""
        if cls._mt_block_patterns is not None:
            return
        cls._build_moderation_term_patterns()

    @classmethod
    def _build_moderation_term_patterns(cls):
        """Compile all active ModerationTerm entries into pattern lists, grouped by severity."""
        block_patterns = []
        flag_patterns = []
        low_patterns = []

        rows = ModerationTerm.objects.filter(is_active=True).values(
            'term', 'match_type', 'severity'
        )
        for row in rows:
            pattern = _compile_term_pattern(row['term'], row['match_type'])
            if pattern is None:
                continue
            entry = (pattern, row['term'])
            severity = row['severity']
            if severity in (ModerationTerm.Severity.CRITICAL, ModerationTerm.Severity.HIGH):
                block_patterns.append(entry)
            elif severity == ModerationTerm.Severity.MEDIUM:
                flag_patterns.append(entry)
            else:
                low_patterns.append(entry)

        cls._mt_block_patterns = block_patterns
        cls._mt_flag_patterns = flag_patterns
        cls._mt_low_patterns = low_patterns
        logger.info(
            'ModerationTerm cache built: %d block, %d flag, %d low patterns',
            len(block_patterns), len(flag_patterns), len(low_patterns),
        )

    @classmethod
    def _match_patterns(cls, text: str, patterns: list) -> str:
        """Return the term string of the first matching pattern, or ''."""
        for compiled, term_str in patterns:
            if compiled.search(text):
                return term_str
        return ''

    @classmethod
    def _contains_term(cls, text: str, terms: list) -> str:
        """Returns the first matched term or empty string (legacy word-boundary check)."""
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
        cls._ensure_moderation_term_patterns()
        body = message.body

        # 1. Check legacy BlockedTerm list
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
            cls._notify_sender_blocked(message, reason='')
            return ModerationResult('blocked', blocked_hit)

        # 2. Check legacy FlaggedTerm list
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
            cls._alert_staff(message, flagged_hit)
            cls._notify_sender_flagged(message)
            return ModerationResult('flagged', flagged_hit)

        # 3. Check ModerationTerm block patterns (CRITICAL + HIGH severity)
        mt_block_hit = cls._match_patterns(body, cls._mt_block_patterns)
        if mt_block_hit:
            message.status = Message.Status.BLOCKED
            message.moderation_note = f'Blocked: matched term "{mt_block_hit}"'
            message.save(update_fields=['status', 'moderation_note'])
            ModerationLog.objects.create(
                message=message,
                action=ModerationLog.Action.BLOCKED,
                triggered_term=mt_block_hit,
            )
            logger.warning('Message #%d blocked (ModerationTerm) – term: %s', message.pk, mt_block_hit)
            cls._notify_sender_blocked(message, reason='')
            return ModerationResult('blocked', mt_block_hit)

        # 4. Check ModerationTerm flag patterns (MEDIUM severity)
        mt_flag_hit = cls._match_patterns(body, cls._mt_flag_patterns)
        if mt_flag_hit:
            message.status = Message.Status.FLAGGED
            message.moderation_note = f'Flagged: matched term "{mt_flag_hit}"'
            message.save(update_fields=['status', 'moderation_note'])
            ModerationLog.objects.create(
                message=message,
                action=ModerationLog.Action.FLAGGED,
                triggered_term=mt_flag_hit,
            )
            logger.warning('Message #%d flagged (ModerationTerm) – term: %s', message.pk, mt_flag_hit)
            cls._alert_staff(message, mt_flag_hit)
            cls._notify_sender_flagged(message)
            return ModerationResult('flagged', mt_flag_hit)

        # 5. Check ModerationTerm LOW patterns — deliver but log
        mt_low_hit = cls._match_patterns(body, cls._mt_low_patterns)
        if mt_low_hit:
            message.status = Message.Status.DELIVERED
            message.save(update_fields=['status'])
            ModerationLog.objects.create(
                message=message,
                action=ModerationLog.Action.APPROVED,
                triggered_term=mt_low_hit,
                notes='LOW severity — delivered with soft-warn log entry',
            )
            logger.info('Message #%d delivered with low-severity log – term: %s', message.pk, mt_low_hit)
            return ModerationResult('delivered', mt_low_hit)

        # 6. Passed all checks — deliver
        message.status = Message.Status.DELIVERED
        message.save(update_fields=['status'])
        return ModerationResult('delivered')

    @classmethod
    def _alert_staff(cls, message, triggered_term):
        """Email all active staff/admin users and create their in-app notification."""
        from django.conf import settings
        from django.core.mail import send_mail
        from apps.users.models import User
        from apps.notifications.models import Notification

        admin_url = (
            f'{settings.CSRF_TRUSTED_ORIGINS[0]}/admin/messaging/message/{message.pk}/change/'
        )
        subject = f'[SPT Moderation] Flagged message requires review (#{message.pk})'
        body = (
            f'A message has been flagged for review.\n\n'
            f'Sender:       {message.sender.full_name} ({message.sender.email})\n'
            f'Triggered by: "{triggered_term}"\n'
            f'Preview:      {message.body[:200]}\n\n'
            f'Review it here: {admin_url}\n'
        )

        staff_users = User.objects.filter(is_active=True).filter(
            models.Q(is_staff=True) | models.Q(role='admin')
        )

        emails = [u.email for u in staff_users if u.email]
        if emails:
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.MENTORING_FROM_EMAIL,
                    recipient_list=emails,
                    fail_silently=True,
                )
            except Exception:
                logger.exception('Failed to send moderation alert emails')

        for admin in staff_users:
            try:
                Notification.objects.create(
                    user=admin,
                    notification_type=Notification.Type.SYSTEM,
                    title='Flagged message requires review',
                    body=f'Message from {message.sender.full_name} matched term "{triggered_term}"',
                    link=f'/admin/messaging/message/{message.pk}/change/',
                )
            except Exception:
                logger.exception('Failed to create moderation notification for user %d', admin.pk)

    @classmethod
    def _notify_sender_flagged(cls, message):
        """M1: Notify the sender that their message is held for moderation review.
        Creates a persistent in-app Notification so the sender still has feedback
        after a page refresh (the real-time HTTP/WS response is transient)."""
        from apps.notifications.models import Notification
        try:
            Notification.objects.create(
                user=message.sender,
                notification_type=Notification.Type.SYSTEM,
                title='Your message is being reviewed',
                body=(
                    'Your message has been held for review by our moderation team. '
                    'It will be delivered once approved. '
                    'You will be notified of the outcome.'
                ),
                link='/messages',
            )
        except Exception:
            logger.exception(
                'Failed to send flagged notification to sender %d', message.sender_id
            )

    @classmethod
    def approve(cls, message, admin_user, notes=''):
        """Admin approves a flagged message."""
        from apps.messaging.models import Message
        message.status = Message.Status.DELIVERED
        message.moderated_by = admin_user
        message.moderated_at = timezone.now()
        message.moderation_note = notes or 'Approved by admin'
        message.save(update_fields=['status', 'moderated_by', 'moderated_at', 'moderation_note'])
        try:
            ModerationLog.objects.create(
                message=message,
                action=ModerationLog.Action.APPROVED,
                actioned_by=admin_user,
                notes=notes,
            )
        except Exception:
            logger.exception('Failed to create ModerationLog for approve on message #%d', message.pk)

    @classmethod
    def reject(cls, message, admin_user, notes=''):
        """Admin rejects a flagged message.

        The status is saved first, then the audit log is created, and finally
        the sender notification is sent.  The log creation is wrapped in
        try/except so that a missing migration or DB error does NOT prevent the
        sender notification from being dispatched — the notification is the most
        user-visible part of this operation and must always fire.
        """
        from apps.messaging.models import Message
        message.status = Message.Status.BLOCKED
        message.moderated_by = admin_user
        message.moderated_at = timezone.now()
        message.moderation_note = notes or 'Rejected by admin'
        message.save(update_fields=['status', 'moderated_by', 'moderated_at', 'moderation_note'])
        try:
            ModerationLog.objects.create(
                message=message,
                action=ModerationLog.Action.REJECTED,
                actioned_by=admin_user,
                notes=notes,
            )
        except Exception:
            logger.exception('Failed to create ModerationLog for reject on message #%d', message.pk)
        # Always notify the sender — must run even if log creation failed above.
        cls._notify_sender_blocked(message, notes)

    @classmethod
    def _notify_sender_blocked(cls, message, reason=''):
        """Send an in-app notification AND a conversation system message to the sender
        explaining why their message was blocked after moderation review."""
        from apps.notifications.models import Notification
        body = reason.strip() if reason.strip() else (
            'Your message was reviewed by a moderator and has been permanently blocked.'
        )
        try:
            Notification.objects.create(
                user=message.sender,
                notification_type=Notification.Type.SYSTEM,
                title='Your message has been blocked by a moderator',
                body=body,
                link='/messages',
            )
        except Exception:
            logger.exception('Failed to send block notification to sender %d', message.sender_id)

        # Also post a visible system message from Arkwright in the same conversation thread
        # so the sender sees clear in-chat feedback without needing to check notifications.
        try:
            from apps.users.models import User
            from apps.messaging.models import Message as Msg
            arkwright, _ = User.objects.get_or_create(
                email='arkwright@spt.org',
                defaults={
                    'username': 'arkwright',
                    'first_name': 'Arkwright',
                    'last_name': '',
                    'role': 'admin',
                    'is_active': True,
                    'notification_email': False,
                    'is_verified': True,
                },
            )
            system_body = (
                f'⚠️ Your recent message was reviewed by a moderator and could not be delivered. '
                f'Reason: {body}'
            )
            Msg.objects.create(
                conversation=message.conversation,
                sender=arkwright,
                body=system_body,
                status=Msg.Status.DELIVERED,
            )
        except Exception:
            logger.exception(
                'Failed to post system block message in conversation %d', message.conversation_id
            )
