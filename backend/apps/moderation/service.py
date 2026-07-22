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
The service also checks the ModerationTerm table (text rules + emoji rules).

Text rule severity → score:
  CRITICAL → 100   HIGH → 80   MEDIUM → 50   LOW → 20

Emoji rule type + severity → score:
  EMOJI_COMBO HIGH/MEDIUM  → 80/50
  EMOJI_OR_SET HIGH/MEDIUM → 60/40
  EMOJI_SINGLE HIGH        → 30
  EMOJI_SINGLE MEDIUM      → 15
  EMOJI_SINGLE LOW         → 5

Score boosts:
  Any text rule + any emoji rule fire on the same message → +20

Score → action:
  ≥ 80   → BLOCKED + admin alert
  50–79  → FLAGGED (held for review)
  20–49  → DELIVERED, logged for admin review queue
  < 20   → DELIVERED, audit-log only

Emoji matching is grapheme-cluster-aware.  Skin-tone modifiers and variation
selectors are stripped before comparison so 🍆🏿 matches a 🍆 rule.

Cache invalidation:
  Call ModerationService.invalidate_cache() to force a full rebuild.
  The import commands do this automatically after each run.
"""
import itertools
import re
import logging
from dataclasses import dataclass, field
from django.conf import settings
from django.db import models
from django.utils import timezone
from .models import BlockedTerm, FlaggedTerm, ModerationLog, ModerationTerm

logger = logging.getLogger('apps.moderation')

EMOJI_COMBO_PROXIMITY: int = getattr(settings, 'EMOJI_COMBO_PROXIMITY', 10)


# ---------------------------------------------------------------------------
# ModerationResult — public return type of screen()
# ---------------------------------------------------------------------------

@dataclass
class ModerationResult:
    status: str                           # 'delivered' | 'flagged' | 'blocked'
    triggered_term: str = ''              # first matched term (backwards-compat)
    triggered_rules: list = field(default_factory=list)
    max_severity: str = ''
    emoji_only_hit: bool = False          # True if only emoji rules fired
    single_emoji_only: bool = False       # True if only EMOJI_SINGLE rules fired
    score: int = 0
    note: str = ''                        # human-readable moderation note for the record


# ---------------------------------------------------------------------------
# Contact-detail detection — shared by direct messages and forum posts.
#
# Contact details (email, bare '@', UK mobile/landline, international numbers)
# are HELD for admin review, never auto-blocked.  This is the same ruleset the
# forum contact check (FOR-02) uses; keeping it in one place guarantees forum
# posts and messages behave identically (MSG-04 / FOR-02 alignment).
# ---------------------------------------------------------------------------

_CONTACT_PATTERNS = [
    (re.compile(r'[\w.+\-]+@[\w.\-]+\.[a-z]{2,}', re.IGNORECASE), 'email address'),
    (re.compile(r'@'),                                               'contact detail (@)'),
    (re.compile(r'\b07\d{3}[\s\-.]?\d{3}[\s\-.]?\d{3}\b'),           'phone number'),
    (re.compile(r'\b(\+44|0[1-9]\d)[\s\-.]?\d{3,4}[\s\-.]?\d{4,6}\b'), 'phone number'),
    (re.compile(r'\+\d{1,4}[\s\-.]?\d{6,14}'),                       'phone number'),
]


def detect_contact_detail(text: str) -> str | None:
    """Return a moderation note if the text shares a contact detail, else None."""
    for pattern, label in _CONTACT_PATTERNS:
        if pattern.search(text):
            return f'Flagged: contains {label}'
    return None


# ---------------------------------------------------------------------------
# Text pattern compilation helpers
# ---------------------------------------------------------------------------

def _email_glob_to_regex(term: str) -> re.Pattern:
    """
    Convert an email-style glob term to a compiled regex.

    '*@hotmail.com'  →  [\\w.+-]+@hotmail\\.com
    '*@*'            →  general email shape
    '@'              →  general email shape
    '@gmail.com'     →  [\\w.+-]+@gmail\\.com
    """
    generic_email = re.compile(r'[\w.+\-]+@[\w.\-]+\.[a-z]{2,}', re.IGNORECASE)

    if term in ('@', '*@*'):
        return generic_email

    if term.startswith('*@') or term.startswith('@'):
        domain_part = term.lstrip('*').lstrip('@')
        if domain_part:
            return re.compile(r'[\w.+\-]+@' + re.escape(domain_part), re.IGNORECASE)
        return generic_email

    return generic_email


def _compile_term_pattern(term: str, match_type: str) -> re.Pattern | None:
    """Compile and return a regex Pattern for the given term and match_type.
    Returns None for emoji match types (handled separately)."""
    try:
        if match_type == ModerationTerm.MatchType.EXACT:
            return re.compile(r'(?i)\b' + re.escape(term) + r'\b')
        elif match_type == ModerationTerm.MatchType.SUBSTRING:
            return re.compile(re.escape(term), re.IGNORECASE)
        elif match_type == ModerationTerm.MatchType.WILDCARD:
            escaped = re.escape(term).replace(r'\*', '.*')
            return re.compile(escaped, re.IGNORECASE)
        elif match_type == ModerationTerm.MatchType.REGEX:
            return re.compile(term, re.IGNORECASE)
        elif match_type == ModerationTerm.MatchType.EMAIL_PATTERN:
            return _email_glob_to_regex(term)
        elif match_type == ModerationTerm.MatchType.URL_FRAGMENT:
            return re.compile(re.escape(term), re.IGNORECASE)
        # EMOJI_* types are handled by the emoji rule cache — return None here.
    except re.error:
        logger.warning('ModerationTerm: invalid pattern skipped — term=%r match_type=%s', term, match_type)
    return None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {
    ModerationTerm.Severity.CRITICAL: 4,
    ModerationTerm.Severity.HIGH: 3,
    ModerationTerm.Severity.MEDIUM: 2,
    ModerationTerm.Severity.LOW: 1,
    '': 0,
}


def compute_score(text_hits: list[dict], emoji_hits: list[dict]) -> int:
    """
    Compute a numeric moderation risk score from collected rule hits.

    text_hits and emoji_hits are lists of rule-hit dicts, each containing at
    least {'severity': ..., 'match_type': ...}.

    This is a plain function so it can be unit-tested without a message object.
    """
    score = 0

    for hit in text_hits:
        sev = hit.get('severity', '')
        if sev == ModerationTerm.Severity.CRITICAL:
            score += 100
        elif sev == ModerationTerm.Severity.HIGH:
            score += 80
        elif sev == ModerationTerm.Severity.MEDIUM:
            score += 50
        elif sev == ModerationTerm.Severity.LOW:
            score += 20

    for hit in emoji_hits:
        mt = hit.get('match_type', '')
        sev = hit.get('severity', '')

        if mt == ModerationTerm.MatchType.EMOJI_COMBO:
            if sev == ModerationTerm.Severity.HIGH:
                score += 80
            elif sev == ModerationTerm.Severity.MEDIUM:
                score += 50
            else:
                score += 20

        elif mt == ModerationTerm.MatchType.EMOJI_OR_SET:
            if sev in (ModerationTerm.Severity.HIGH, ModerationTerm.Severity.CRITICAL):
                score += 60
            elif sev == ModerationTerm.Severity.MEDIUM:
                score += 40
            else:
                score += 10

        elif mt == ModerationTerm.MatchType.EMOJI_SINGLE:
            if sev == ModerationTerm.Severity.HIGH:
                score += 30
            elif sev == ModerationTerm.Severity.MEDIUM:
                score += 15
            else:
                score += 5

    # Cross-signal boost: text + emoji together on one message.
    if text_hits and emoji_hits:
        score += 20

    return score


def _max_severity(hits: list[dict]) -> str:
    """Return the highest severity string from a list of hit dicts."""
    best = ''
    best_rank = 0
    for hit in hits:
        sev = hit.get('severity', '')
        rank = _SEVERITY_ORDER.get(sev, 0)
        if rank > best_rank:
            best_rank = rank
            best = sev
    return best


# ---------------------------------------------------------------------------
# Emoji proximity check
# ---------------------------------------------------------------------------

def _combo_fires(emoji_list: list[str], combo_parts: list[str], proximity: int) -> bool:
    """
    Return True if every element of *combo_parts* appears in *emoji_list* AND
    the maximum index-distance between any two parts is ≤ *proximity*.
    """
    if not combo_parts:
        return False
    positions: dict[str, list[int]] = {}
    for part in combo_parts:
        idxs = [i for i, e in enumerate(emoji_list) if e == part]
        if not idxs:
            return False
        positions[part] = idxs

    for combo in itertools.product(*positions.values()):
        if max(combo) - min(combo) <= proximity:
            return True
    return False


# ---------------------------------------------------------------------------
# ModerationService
# ---------------------------------------------------------------------------

def build_moderation_alert(sender_name, sender_email, triggered_term, admin_url, message_pk, message_body):
    subject = f'[SPT Moderation] Flagged message requires review (#{message_pk})'
    body = (
        f'A message has been flagged for review.\n\n'
        f'Sender:       {sender_name} ({sender_email})\n'
        f'Triggered by: "{triggered_term}"\n'
        f'Preview:      {message_body[:200]}\n\n'
        f'Review it here: {admin_url}\n'
    )
    return subject, body


class ModerationService:
    # Legacy term caches — reloaded fresh on every screen() call.
    _blocked_terms_cache = None
    _flagged_terms_cache = None

    # Compiled ModerationTerm text-pattern cache — built once, invalidated explicitly.
    _mt_block_patterns: list | None = None
    _mt_flag_patterns: list | None = None
    _mt_low_patterns: list | None = None

    # Emoji rule cache — list of rule dicts, built once alongside text patterns.
    # Each entry: {term, match_type, severity, category, combo_parts (COMBO only)}
    _emoji_rules_cache: list | None = None

    @classmethod
    def invalidate_cache(cls):
        """Force the next screen() call to rebuild all caches from the database."""
        cls._blocked_terms_cache = None
        cls._flagged_terms_cache = None
        cls._mt_block_patterns = None
        cls._mt_flag_patterns = None
        cls._mt_low_patterns = None
        cls._emoji_rules_cache = None

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
        """Build compiled text-pattern lists and emoji rule cache if not already cached."""
        if cls._mt_block_patterns is not None:
            return
        cls._build_moderation_term_patterns()

    @classmethod
    def _build_moderation_term_patterns(cls):
        """
        Compile all active ModerationTerm entries into caches.

        Text match types (EXACT, SUBSTRING, WILDCARD, REGEX, EMAIL_PATTERN,
        URL_FRAGMENT) go into the pattern lists grouped by severity.

        Emoji match types (EMOJI_SINGLE, EMOJI_COMBO, EMOJI_OR_SET) go into
        the emoji rules cache as structured dicts for grapheme-aware matching.
        """
        from .utils.emoji import extract_emoji_graphemes

        block_patterns = []
        flag_patterns = []
        low_patterns = []
        emoji_rules = []

        emoji_types = {
            ModerationTerm.MatchType.EMOJI_SINGLE,
            ModerationTerm.MatchType.EMOJI_COMBO,
            ModerationTerm.MatchType.EMOJI_OR_SET,
        }

        rows = ModerationTerm.objects.filter(is_active=True).values(
            'term', 'match_type', 'severity', 'category'
        )
        for row in rows:
            mt = row['match_type']
            if mt in emoji_types:
                rule = {
                    'term': row['term'],
                    'match_type': mt,
                    'severity': row['severity'],
                    'category': row['category'],
                }
                if mt == ModerationTerm.MatchType.EMOJI_COMBO:
                    # Pre-split combo pattern into individual emoji for proximity matching.
                    rule['combo_parts'] = extract_emoji_graphemes(row['term'])
                emoji_rules.append(rule)
                continue

            # Contact details (email/@ patterns) are handled by the shared
            # detect_contact_detail() check, which always HOLDS them for review
            # rather than blocking (MSG-04).  Skip them here so a HIGH-severity
            # EMAIL_PATTERN term can never push a message onto the block path.
            if mt == ModerationTerm.MatchType.EMAIL_PATTERN:
                continue

            pattern = _compile_term_pattern(row['term'], mt)
            if pattern is None:
                continue

            sev = row['severity']
            # Shared links (URL fragments) are likewise contact-leak signals and
            # are HELD for review, not auto-blocked — force them to the flag tier.
            if mt == ModerationTerm.MatchType.URL_FRAGMENT:
                sev = ModerationTerm.Severity.MEDIUM

            entry = (pattern, row['term'], sev, mt)
            if sev in (ModerationTerm.Severity.CRITICAL, ModerationTerm.Severity.HIGH):
                block_patterns.append(entry)
            elif sev == ModerationTerm.Severity.MEDIUM:
                flag_patterns.append(entry)
            else:
                low_patterns.append(entry)

        cls._mt_block_patterns = block_patterns
        cls._mt_flag_patterns = flag_patterns
        cls._mt_low_patterns = low_patterns
        cls._emoji_rules_cache = emoji_rules
        logger.info(
            'ModerationTerm cache built: %d block, %d flag, %d low text patterns; %d emoji rules',
            len(block_patterns), len(flag_patterns), len(low_patterns), len(emoji_rules),
        )

    @classmethod
    def _collect_text_hits(cls, text: str) -> list[dict]:
        """Return all matching text-rule hits as dicts with term/severity.

        ``match_type`` here is the ORIGINAL ModerationTerm.MatchType the term
        was defined with (EXACT/SUBSTRING/WILDCARD/REGEX/URL_FRAGMENT), not a
        generic 'text' placeholder, so downstream code (e.g.
        sender_facing_reason) can tell a URL-fragment hit apart from any other
        text-rule hit.
        """
        hits = []
        for patterns_list in (cls._mt_block_patterns, cls._mt_flag_patterns, cls._mt_low_patterns):
            for compiled, term_str, severity, match_type in patterns_list:
                if compiled.search(text):
                    hits.append({
                        'term': term_str,
                        'match_type': match_type,
                        'severity': severity,
                        'source': 'text',
                    })
        return hits

    @classmethod
    def _collect_emoji_hits(cls, text: str) -> list[dict]:
        """Return all matching emoji-rule hits, grapheme-cluster-aware."""
        from .utils.emoji import extract_emoji_graphemes, normalise_emoji

        if not cls._emoji_rules_cache:
            return []

        # Build normalised emoji list once for this message.
        raw_clusters = extract_emoji_graphemes(text)
        norm_list = [normalise_emoji(g) for g in raw_clusters]
        if not norm_list:
            return []

        norm_seq = ''.join(norm_list)

        hits = []
        proximity = EMOJI_COMBO_PROXIMITY

        for rule in cls._emoji_rules_cache:
            mt = rule['match_type']
            pattern = rule['term']  # normalised pattern stored at import time

            if mt == ModerationTerm.MatchType.EMOJI_SINGLE:
                if pattern in norm_seq:
                    hits.append({
                        'term': pattern,
                        'match_type': mt,
                        'severity': rule['severity'],
                        'category': rule['category'],
                        'source': 'emoji',
                    })

            elif mt == ModerationTerm.MatchType.EMOJI_OR_SET:
                if pattern in norm_seq:
                    hits.append({
                        'term': pattern,
                        'match_type': mt,
                        'severity': rule['severity'],
                        'category': rule['category'],
                        'source': 'emoji',
                    })

            elif mt == ModerationTerm.MatchType.EMOJI_COMBO:
                combo_parts = rule.get('combo_parts', [])
                if combo_parts and _combo_fires(norm_list, combo_parts, proximity):
                    hits.append({
                        'term': pattern,
                        'match_type': mt,
                        'severity': rule['severity'],
                        'category': rule['category'],
                        'source': 'emoji',
                    })

        return hits

    @classmethod
    def _match_patterns(cls, text: str, patterns: list) -> str:
        """Return the term string of the first matching pattern, or ''."""
        for compiled, term_str, *_ in patterns:
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
    def screen_text(cls, body: str) -> ModerationResult:
        """
        Screen a raw text body and return a ModerationResult WITHOUT touching any
        model.  Shared by direct messages (screen()) and forum posts so both
        behave identically.

        Decision order:
          1. Legacy BlockedTerm           → blocked (stops delivery; MOD-04)
          2. ModerationTerm score ≥ 80    → blocked (genuine block-tier content)
          3. Contact detail / legacy
             FlaggedTerm / score ≥ 50     → flagged (held for review; MSG-04/FOR-02)
          4. score ≥ 20                   → delivered, logged for review queue
          5. otherwise                    → delivered (audit only)

        Contact details (email, bare '@', phone numbers) are detected by the
        shared detect_contact_detail() check and are always HELD, never blocked.
        """
        cls._load_terms()
        cls._ensure_moderation_term_patterns()

        # 1. Legacy BlockedTerm — immediate block.
        blocked_hit = cls._contains_term(body, cls._blocked_terms_cache)
        if blocked_hit:
            return ModerationResult(
                status='blocked', triggered_term=blocked_hit, score=100,
                max_severity=ModerationTerm.Severity.CRITICAL,
                note=f'Blocked: matched term "{blocked_hit}"',
            )

        # 2. Collect ModerationTerm hits (text + emoji) and score together.
        text_hits = cls._collect_text_hits(body)
        emoji_hits = cls._collect_emoji_hits(body)
        all_hits = text_hits + emoji_hits
        score = compute_score(text_hits, emoji_hits)
        max_sev = _max_severity(all_hits)
        emoji_only = bool(emoji_hits) and not bool(text_hits)
        single_only = emoji_only and all(
            h['match_type'] == ModerationTerm.MatchType.EMOJI_SINGLE for h in emoji_hits
        )
        first_term = all_hits[0]['term'] if all_hits else ''

        # Genuine block-tier content stops delivery outright.
        if score >= 80:
            return ModerationResult(
                status='blocked', triggered_term=first_term, triggered_rules=all_hits,
                max_severity=max_sev, emoji_only_hit=emoji_only,
                single_emoji_only=single_only, score=score,
                note=f'Blocked: score={score}, term="{first_term}"',
            )

        # 3. Contact details and legacy FlaggedTerm hits are HELD for review.
        contact_note = detect_contact_detail(body)
        flagged_hit = cls._contains_term(body, cls._flagged_terms_cache)

        if score >= 50 or contact_note or flagged_hit:
            if contact_note and score < 50 and not flagged_hit:
                note = contact_note
                triggered = contact_note
                sev = ModerationTerm.Severity.MEDIUM
            elif flagged_hit and score < 50:
                note = f'Flagged: matched term "{flagged_hit}"'
                triggered = flagged_hit
                sev = ModerationTerm.Severity.MEDIUM
            else:
                note = f'Flagged: score={score}, term="{first_term}"'
                triggered = first_term
                sev = max_sev or ModerationTerm.Severity.MEDIUM
            return ModerationResult(
                status='flagged', triggered_term=triggered, triggered_rules=all_hits,
                max_severity=sev, emoji_only_hit=emoji_only,
                single_emoji_only=single_only, score=max(score, 50), note=note,
            )

        # 4/5. Lower scores deliver (review queue or audit only).
        if all_hits:
            queue = score >= 20
            return ModerationResult(
                status='delivered', triggered_term=first_term, triggered_rules=all_hits,
                max_severity=max_sev, emoji_only_hit=emoji_only,
                single_emoji_only=single_only, score=score,
                note=(f'score={score} — delivered, queued for review' if queue
                      else f'score={score} — delivered, audit log only'),
            )
        return ModerationResult(status='delivered', score=0)

    @classmethod
    def sender_facing_reason(cls, result) -> str:
        """A safe, category-level explanation of why a message was held or
        blocked, suitable for showing to the sender who wrote it.

        This must NEVER reveal the specific term, phrase or word list that
        matched, only the broad category, so the block/flag list itself is
        never exposed to end users.
        """
        note = (result.note or '').lower()
        rules = result.triggered_rules or []
        if any(r.get('match_type') == ModerationTerm.MatchType.URL_FRAGMENT for r in rules):
            return 'it contains a web link'
        if 'email' in note or 'phone' in note or '@' in note or 'contact' in note:
            return 'it appears to contain contact details (such as an email address or phone number)'
        return 'it contains wording that is not permitted on the platform'

    @classmethod
    def screen(cls, message) -> ModerationResult:
        """
        Screen a Message instance: delegate the decision to screen_text(), then
        apply the resulting status, write a ModerationLog entry and dispatch the
        sender/staff notifications.
        """
        from apps.messaging.models import Message

        try:
            result = cls.screen_text(message.body)
        except Exception:
            logger.exception(
                'Moderation pipeline error on message #%d — held for admin review',
                message.pk,
            )
            message.status = Message.Status.FLAGGED
            message.moderation_note = 'Pipeline error — held for admin review'
            message.save(update_fields=['status', 'moderation_note'])
            return ModerationResult(status='flagged', score=0)

        triggered = result.triggered_term

        if result.status == 'blocked':
            message.status = Message.Status.BLOCKED
            message.moderation_note = result.note
            message.save(update_fields=['status', 'moderation_note'])
            ModerationLog.objects.create(
                message=message, action=ModerationLog.Action.BLOCKED,
                triggered_term=triggered, notes=f'score={result.score}',
            )
            logger.warning('Message #%d blocked (score=%d) – term: %s',
                           message.pk, result.score, triggered)
            # Auto-block: do NOT claim a moderator reviewed it (MSG-04).
            cls._notify_sender_blocked(message, reason='', auto=True)
            cls._alert_staff(message, triggered)

        elif result.status == 'flagged':
            message.status = Message.Status.FLAGGED
            message.moderation_note = result.note
            message.save(update_fields=['status', 'moderation_note'])
            ModerationLog.objects.create(
                message=message, action=ModerationLog.Action.FLAGGED,
                triggered_term=triggered, notes=f'score={result.score}',
            )
            logger.warning('Message #%d flagged (score=%d) – term: %s',
                           message.pk, result.score, triggered)
            cls._alert_staff(message, triggered)
            cls._notify_sender_flagged(message)

        else:  # delivered
            message.status = Message.Status.DELIVERED
            message.save(update_fields=['status'])
            if result.triggered_rules:
                ModerationLog.objects.create(
                    message=message, action=ModerationLog.Action.APPROVED,
                    triggered_term=triggered, notes=result.note,
                )
            logger.info('Message #%d delivered (score=%d) – term: %s',
                        message.pk, result.score, triggered)

        return result

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
        subject, body = build_moderation_alert(
            message.sender.full_name, message.sender.email, triggered_term,
            admin_url, message.pk, message.body,
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
        """Notify the sender that their message is held for moderation review."""
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
        cls._notify_sender_blocked(message, notes)

    @classmethod
    def _notify_sender_blocked(cls, message, reason='', auto=False):
        """Send an in-app notification AND a conversation system message to the sender
        explaining why their message was blocked.

        ``auto=True`` means the block was an automatic screening decision with no
        human involvement — in that case we must NOT tell the sender a moderator
        reviewed it (MSG-04).  ``auto=False`` is used by reject(), where an admin
        genuinely reviewed and blocked the message.
        """
        from apps.notifications.models import Notification
        if reason.strip():
            body = reason.strip()
            title = 'Your message has been blocked by a moderator'
        elif auto:
            body = (
                'Your message could not be delivered because it contains content '
                'that is not permitted on the platform.'
            )
            title = 'Your message could not be delivered'
        else:
            body = 'Your message was reviewed by a moderator and has been permanently blocked.'
            title = 'Your message has been blocked by a moderator'
        try:
            Notification.objects.create(
                user=message.sender,
                notification_type=Notification.Type.SYSTEM,
                title=title,
                body=body,
                link='/messages',
            )
        except Exception:
            logger.exception('Failed to send block notification to sender %d', message.sender_id)

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
            if auto and not reason.strip():
                system_body = (
                    'Your recent message could not be delivered because it contains '
                    'content that is not permitted on the platform.'
                )
            else:
                system_body = (
                    'Your recent message was reviewed by a moderator and could not be '
                    f'delivered. Reason: {body}'
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
