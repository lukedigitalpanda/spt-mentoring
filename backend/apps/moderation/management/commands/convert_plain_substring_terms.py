"""
Convert plain-letter SUBSTRING moderation terms to word-boundary (EXACT) matching.

Why
───
Bulk import created ~968 plain alphabetic terms with match_type=SUBSTRING, which
match *inside* innocent words ('af' in afternoon, 'tit' in title, 'kill' in
skills, 'anal' in analysis). EXACT compiles to (?i)\\b<term>\\b, so the term only
matches as a whole word. Obfuscated terms (containing a digit, symbol or space —
e.g. '5h1t', 'a$$', 'blow job') are LEFT as SUBSTRING: they never appear inside
real words, and substring is exactly what catches that evasion.

See docs/superpowers/specs/2026-06-30-moderation-wordboundary-design.md.

Usage
─────
    python manage.py convert_plain_substring_terms --dry-run   # report only
    python manage.py convert_plain_substring_terms             # apply
"""
import re

from django.core.management.base import BaseCommand

from apps.moderation.models import ModerationTerm
from apps.moderation.service import ModerationService

PLAIN_ALPHA = re.compile(r'^[A-Za-z]+$')


class Command(BaseCommand):
    help = 'Convert plain-letter SUBSTRING moderation terms to EXACT (word-boundary) matching.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would change without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        candidates = [
            t for t in ModerationTerm.objects.filter(
                match_type=ModerationTerm.MatchType.SUBSTRING
            )
            if PLAIN_ALPHA.match(t.term)
        ]

        self.stdout.write(
            f'Found {len(candidates)} plain-letter SUBSTRING term(s) to convert '
            f'to word-boundary (EXACT) matching.'
        )
        sample = ', '.join(t.term for t in candidates[:15])
        if sample:
            self.stdout.write(f'  e.g. {sample}')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — no changes made.'))
            return

        # Terms that already exist as EXACT would violate unique_together
        # ('term', 'match_type'); drop the SUBSTRING duplicate instead of updating.
        existing_exact = set(
            ModerationTerm.objects.filter(
                match_type=ModerationTerm.MatchType.EXACT
            ).values_list('term', flat=True)
        )

        converted = 0
        deduped = 0
        for term in candidates:
            if term.term in existing_exact:
                term.delete()
                deduped += 1
                continue
            term.match_type = ModerationTerm.MatchType.EXACT
            term.save(update_fields=['match_type'])
            existing_exact.add(term.term)
            converted += 1

        ModerationService.invalidate_cache()

        self.stdout.write(self.style.SUCCESS(
            f'Converted {converted} term(s) to EXACT'
            + (f', removed {deduped} duplicate(s) of existing EXACT terms' if deduped else '')
            + '. Moderation cache invalidated.'
        ))
        self.stdout.write(self.style.WARNING(
            'Restart the backend (daphne, no hot-reload) for the running process '
            'to pick up the rebuilt patterns.'
        ))
