"""
Import a plain-text list of moderation terms into ModerationTerm.

Usage:
    python manage.py import_moderation_terms
    python manage.py import_moderation_terms --file data/moderation/moderation_terms.txt
    python manage.py import_moderation_terms --dry-run
    python manage.py import_moderation_terms --deactivate-missing

Classification rules (in priority order):

  match_type:
    EMAIL_PATTERN  — term contains '@'
    URL_FRAGMENT   — term is 'http:' or 'www' (or starts with 'http:')
    REGEX          — contains regex metacharacters (?, +, [, (, |) but NOT '@'
    WILDCARD       — contains '*' but NOT '@'
    SUBSTRING      — everything else (including multi-word phrases)

  Substring terms are matched WITHOUT word boundaries so obfuscated variants
  like 'sh1t' inside 'thisissh1ttext' are caught. The false-positive risk for
  very short terms is accepted as the safer default for a safeguarding platform.

  severity (evaluated in priority order):
    CRITICAL — terms on the hardcoded CRITICAL_TERMS set
    LOW      — terms on the hardcoded LOW_TERMS set
    HIGH     — EMAIL_PATTERN, URL_FRAGMENT, hard slurs, explicit sexual terms
    MEDIUM   — default for all other terms

  category — first matching seed in CATEGORY_SEEDS wins; default is PROFANITY.

Safety invariant:
  Rows whose source differs from --source are NEVER updated or deactivated.
  Only bulk_import_v1-sourced rows (or whichever --source is passed) are touched.
"""
import re
import pathlib

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.moderation.models import ModerationTerm

# ---------------------------------------------------------------------------
# Hard-coded severity lists — keep these auditable and explicit.
# ---------------------------------------------------------------------------

CRITICAL_TERMS = frozenset({
    'how to kill', 'how to murder', 'kill', 'murder',
    'rape', 'raped', 'raper', 'rapist',
    'pedo', 'pedophile', 'pedophilia', 'pedophiliac',
    'molest', 'molested', 'molester', 'molestation',
    'incest',
    'suicide', 'suicidal',
    'kms', 'kys',
    'self harm', 'self-harm',
    'child abuse', 'child porn', 'cp',
})

LOW_TERMS = frozenset({
    'damn', 'crap', 'bloody', 'hell', 'stupid', 'dummy',
    'idiot', 'dumb', 'moron', 'jerk',
})

# ---------------------------------------------------------------------------
# High-severity seed keywords — these push a term to HIGH if not CRITICAL/LOW.
# ---------------------------------------------------------------------------

HIGH_SEED_FRAGMENTS = frozenset({
    # contact-leak match types are always HIGH (handled separately)
    # slurs
    'nigger', 'nigga', 'faggot', 'chink', 'spic', 'kike', 'wetback', 'tranny',
    # explicit sexual
    'porn', 'anal', 'vagina', 'penis', 'cock', 'dick', 'pussy',
    'blowjob', 'blow job', 'masterbat', 'masturbat', 'cum shot',
    'fuck', 'fucker', 'fucking', 'fuk', 'f.u.c.k', 'f_u_c_k',
    'sex', 'erect', 'orgasm',
})

# ---------------------------------------------------------------------------
# Category classification — first match wins; default is PROFANITY.
# Keys are ModerationTerm.Category values; values are substrings to look for
# in the lowercased term.
# ---------------------------------------------------------------------------

CATEGORY_SEEDS: list[tuple[str, frozenset]] = [
    (ModerationTerm.Category.CONTACT_LEAK, frozenset({
        '@', 'http:', 'www', 'gmail', 'hotmail', 'live.com', 'teams',
    })),
    (ModerationTerm.Category.SAFEGUARDING, frozenset({
        'kill', 'murder', 'rape', 'molest', 'incest', 'suicide', 'kms', 'kys',
        'self harm', 'self-harm', 'pedo', 'pedophil', 'child abuse', 'child porn',
        'how to', 'abuse',
    })),
    (ModerationTerm.Category.DRUGS_ALCOHOL, frozenset({
        'cocaine', 'heroin', 'meth', 'weed', 'cannabis', 'marijuana', 'crack',
        'ecstasy', 'mdma', 'lsd', 'acid', 'amphetamine', 'ketamine', 'opioid',
        'fentanyl', 'opium', 'drug', 'alcohol', 'booze', 'drunk',
    })),
    (ModerationTerm.Category.VIOLENCE, frozenset({
        'stab', 'shoot', 'gun', 'knife', 'weapon', 'bomb', 'attack',
        'beat', 'punch', 'kick', 'assault', 'cunt punt', 'hit',
    })),
    (ModerationTerm.Category.SEXUAL, frozenset({
        'sex', 'porn', 'anal', 'vagina', 'penis', 'nude', 'naked', 'boob', 'tit',
        'cock', 'dick', 'pussy', 'cunt', 'fuck', 'fucker', 'blow job', 'blowjob',
        'masterbat', 'masturbat', 'orgasm', 'erect', 'cum', 'horny', 'slut',
        'whore', 'hooker', 'bitch', 'rimjob', 'handjob',
    })),
    (ModerationTerm.Category.SLUR, frozenset({
        'nigger', 'nigga', 'faggot', 'fag', 'chink', 'spic', 'kike', 'wetback',
        'tranny', 'retard', 'wanker', 'bastard', 'coon', 'gook', 'dyke',
    })),
]


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def classify_match_type(term: str) -> str:
    """Determine match_type for a raw term string."""
    if '@' in term:
        return ModerationTerm.MatchType.EMAIL_PATTERN
    low = term.lower()
    if low == 'www' or low.startswith('http:') or low == 'http':
        return ModerationTerm.MatchType.URL_FRAGMENT
    # Regex metacharacters — but NOT the wildcard * (handled separately)
    if any(c in term for c in ('?', '+', '[', '(', '|')):
        return ModerationTerm.MatchType.REGEX
    if '*' in term:
        return ModerationTerm.MatchType.WILDCARD
    return ModerationTerm.MatchType.SUBSTRING


def classify_category(term: str, match_type: str) -> str:
    """Return the most specific category, defaulting to PROFANITY."""
    if match_type in (ModerationTerm.MatchType.EMAIL_PATTERN, ModerationTerm.MatchType.URL_FRAGMENT):
        return ModerationTerm.Category.CONTACT_LEAK
    low = term.lower()
    for category, seeds in CATEGORY_SEEDS:
        if any(seed in low for seed in seeds):
            return category
    return ModerationTerm.Category.PROFANITY


def classify_severity(term: str, match_type: str) -> str:
    """Return severity. CRITICAL and LOW are hardcoded; HIGH covers contact-leak
    and known high-risk fragments; everything else is MEDIUM."""
    low = term.lower()

    if low in CRITICAL_TERMS:
        return ModerationTerm.Severity.CRITICAL

    if low in LOW_TERMS:
        return ModerationTerm.Severity.LOW

    # Contact-leak match types always warrant HIGH
    if match_type in (ModerationTerm.MatchType.EMAIL_PATTERN, ModerationTerm.MatchType.URL_FRAGMENT):
        return ModerationTerm.Severity.HIGH

    # Check high-severity seed fragments
    if any(fragment in low for fragment in HIGH_SEED_FRAGMENTS):
        return ModerationTerm.Severity.HIGH

    return ModerationTerm.Severity.MEDIUM


def classify_term(term: str) -> dict:
    """Return a dict of field values for a given raw term string."""
    match_type = classify_match_type(term)
    category = classify_category(term, match_type)
    severity = classify_severity(term, match_type)
    return {
        'match_type': match_type,
        'category': category,
        'severity': severity,
    }


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Import moderation terms from a plain-text file (one term per line).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='data/moderation/moderation_terms.txt',
            help='Path to the terms file (default: data/moderation/moderation_terms.txt)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Print what would happen without writing to the database.',
        )
        parser.add_argument(
            '--source',
            default='bulk_import_v1',
            help='Source tag written to every imported row (default: bulk_import_v1).',
        )
        parser.add_argument(
            '--deactivate-missing',
            action='store_true',
            default=False,
            help=(
                'Deactivate rows with matching --source that are NOT present in '
                'the current file. Never touches rows from other sources.'
            ),
        )

    def handle(self, *args, **options):
        file_path = pathlib.Path(options['file'])
        dry_run: bool = options['dry_run']
        source: str = options['source']
        deactivate_missing: bool = options['deactivate_missing']

        if not file_path.exists():
            raise CommandError(f'Terms file not found: {file_path}')

        raw_lines = file_path.read_text(encoding='utf-8').splitlines()
        terms = [line.strip() for line in raw_lines if line.strip()]
        total_in_file = len(terms)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no database changes will be made.\n'))

        created = updated = skipped_admin = 0

        with transaction.atomic():
            for term in terms:
                classification = classify_term(term)

                try:
                    existing = ModerationTerm.objects.get(
                        term=term, match_type=classification['match_type']
                    )
                except ModerationTerm.DoesNotExist:
                    existing = None

                if existing is not None:
                    if existing.source != source:
                        # Owned by a different source (e.g. 'admin') — never touch it.
                        skipped_admin += 1
                        if dry_run:
                            self.stdout.write(
                                f'  SKIP (source={existing.source}): {term!r}'
                            )
                        continue

                    # Same source — update classification fields and re-activate.
                    changed = (
                        existing.category != classification['category']
                        or existing.severity != classification['severity']
                        or not existing.is_active
                    )
                    if changed:
                        if not dry_run:
                            existing.category = classification['category']
                            existing.severity = classification['severity']
                            existing.is_active = True
                            existing.save(update_fields=['category', 'severity', 'is_active', 'updated_at'])
                        updated += 1
                    # If nothing changed, it still counts as processed (not skipped).
                else:
                    if not dry_run:
                        ModerationTerm.objects.create(
                            term=term,
                            match_type=classification['match_type'],
                            category=classification['category'],
                            severity=classification['severity'],
                            source=source,
                            is_active=True,
                        )
                    created += 1

            if deactivate_missing:
                file_term_set = set(terms)
                # Only deactivate rows that belong to this import source.
                # Build (term, match_type) pairs present in the file.
                file_pairs = {
                    (t, classify_term(t)['match_type']) for t in file_term_set
                }
                to_deactivate = ModerationTerm.objects.filter(
                    source=source, is_active=True
                ).exclude(
                    # Exclude rows whose (term, match_type) pair appears in the file.
                    # Django doesn't support multi-column IN natively, so filter in Python.
                    pk__in=[]  # placeholder — real filtering done below
                )
                deactivated_count = 0
                for row in to_deactivate:
                    if (row.term, row.match_type) not in file_pairs:
                        if not dry_run:
                            row.is_active = False
                            row.save(update_fields=['is_active', 'updated_at'])
                        deactivated_count += 1
                        if dry_run:
                            self.stdout.write(f'  WOULD DEACTIVATE: {row.term!r}')
                if deactivated_count:
                    self.stdout.write(
                        self.style.WARNING(f'Deactivated {deactivated_count} rows not in file.')
                    )

            if dry_run:
                # Roll back everything so no changes persist.
                transaction.set_rollback(True)

        # Invalidate the service pattern cache so the next request uses fresh data.
        if not dry_run:
            try:
                from apps.moderation.service import ModerationService
                ModerationService.invalidate_cache()
            except Exception:
                pass

        self.stdout.write(
            self.style.SUCCESS(
                f'\nImport complete.\n'
                f'  Total in file:           {total_in_file}\n'
                f'  Created:                 {created}\n'
                f'  Updated:                 {updated}\n'
                f'  Skipped (other source):  {skipped_admin}\n'
            )
        )
