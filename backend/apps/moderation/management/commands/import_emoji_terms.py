"""
Import emoji moderation rules from a CSV file into ModerationTerm.

Usage:
    python manage.py import_emoji_terms
    python manage.py import_emoji_terms --file data/moderation/emoji_moderation_terms.csv
    python manage.py import_emoji_terms --dry-run
    python manage.py import_emoji_terms --deactivate-missing

CSV columns: emojis, meaning, context, severity, notes

Classification rules:
  1 emoji grapheme  → EMOJI_SINGLE
  2+ graphemes AND meaning contains '/'  → EMOJI_OR_SET
      One DB row is created PER emoji in the set, all sharing the same meaning.
  2+ graphemes AND meaning does NOT contain '/'  → EMOJI_COMBO
      One DB row is created with the full normalised sequence as the term.
      Rows where the emojis look like independent alternatives rather than a
      gestural combination are flagged as AMBIGUOUS in the log for human review.

Safety invariant:
  Rows whose source differs from --source are NEVER updated or deactivated.

Duplicate handling:
  If the same normalised emoji appears twice in the file with the same
  match_type, the second occurrence is merged into the first (notes combined).
  This handles rows like 👀 which appear twice with different meanings.
"""
import csv
import pathlib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.moderation.models import ModerationTerm
from apps.moderation.utils.emoji import extract_emoji_graphemes, normalise_emoji


# ---------------------------------------------------------------------------
# Context → Category mapping
# ---------------------------------------------------------------------------

_CONTEXT_CATEGORY = {
    'Sexting': ModerationTerm.Category.SEXUAL,
    'Drug selling/buying online': ModerationTerm.Category.DRUGS_ALCOHOL,
    'Drug selling/buying online / class A drugs': ModerationTerm.Category.DRUGS_ALCOHOL,
    'Parent/carer involvement / digital penetration': ModerationTerm.Category.SAFEGUARDING,
    'Safeguarding': ModerationTerm.Category.SAFEGUARDING,
    'Violence': ModerationTerm.Category.VIOLENCE,
}

_SEVERITY_MAP = {
    'LOW': ModerationTerm.Severity.LOW,
    'MEDIUM': ModerationTerm.Severity.MEDIUM,
    'HIGH': ModerationTerm.Severity.HIGH,
    'CRITICAL': ModerationTerm.Severity.CRITICAL,
}

# Rows whose emojis look like independent code-word alternatives rather than a
# gestural sequence — flagged AMBIGUOUS in the import log so a human reviewer
# can decide whether to flip them to EMOJI_OR_SET in the admin UI.
_AMBIGUOUS_MEANINGS = frozenset({
    'Vagina',
    'Cocaine',
    'Breasts',
    'Methamphetamine',
    'Heroin',
    'Sexual intercourse',
    'Spanking',
})


def _map_context(context: str) -> str:
    key = context.strip()
    return _CONTEXT_CATEGORY.get(key, ModerationTerm.Category.OTHER)


def _map_severity(raw: str) -> str:
    return _SEVERITY_MAP.get(raw.strip().upper(), ModerationTerm.Severity.MEDIUM)


def _parse_emojis(raw: str):
    """
    Parse the emojis field as a Unicode grapheme-cluster sequence.
    Returns (graphemes: list[str], normalised_list: list[str]).
    """
    clusters = extract_emoji_graphemes(raw.strip())
    normalised = [normalise_emoji(g) for g in clusters]
    return clusters, normalised


def _is_or_set(meaning: str) -> bool:
    return '/' in meaning


def classify_row(emojis_field: str, meaning: str):
    """
    Return (match_type, patterns, is_ambiguous).

    patterns is a list of normalised emoji strings:
      EMOJI_SINGLE  → [single_emoji]
      EMOJI_COMBO   → [full_concatenated_sequence]
      EMOJI_OR_SET  → [emoji1, emoji2, ...]   (one row per emoji at insert time)
    """
    _clusters, normalised = _parse_emojis(emojis_field)
    n = len(normalised)

    if n == 0:
        return None, [], False

    if n == 1:
        return ModerationTerm.MatchType.EMOJI_SINGLE, normalised, False

    if _is_or_set(meaning):
        return ModerationTerm.MatchType.EMOJI_OR_SET, normalised, False

    # n >= 2, no slash in meaning → COMBO
    is_ambiguous = meaning.strip() in _AMBIGUOUS_MEANINGS
    return ModerationTerm.MatchType.EMOJI_COMBO, [''.join(normalised)], is_ambiguous


class Command(BaseCommand):
    help = 'Import emoji moderation rules from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='data/moderation/emoji_moderation_terms.csv',
            help='Path to the CSV file (default: data/moderation/emoji_moderation_terms.csv)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Print what would happen without writing to the database.',
        )
        parser.add_argument(
            '--source',
            default='emoji_bulk_v1',
            help='Source tag written to every imported row (default: emoji_bulk_v1).',
        )
        parser.add_argument(
            '--deactivate-missing',
            action='store_true',
            default=False,
            help='Deactivate rows with matching --source that are not in the current file.',
        )

    def handle(self, *args, **options):
        file_path = pathlib.Path(options['file'])
        dry_run: bool = options['dry_run']
        source: str = options['source']
        deactivate_missing: bool = options['deactivate_missing']

        if not file_path.exists():
            raise CommandError(f'CSV file not found: {file_path}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no database changes will be made.\n'))

        # Read with explicit UTF-8, strip BOM if Excel round-tripped it.
        try:
            raw_text = file_path.read_bytes().decode('utf-8')
        except UnicodeDecodeError as exc:
            raise CommandError(
                f'File is not valid UTF-8 ({exc}). '
                'Save the CSV as UTF-8 (not UTF-16 or Latin-1) and retry.'
            ) from exc

        if raw_text.startswith('﻿'):
            raw_text = raw_text[1:]

        lines = raw_text.splitlines()
        if not lines:
            raise CommandError('CSV file is empty.')

        reader = csv.DictReader(lines)
        rows = list(reader)

        if not rows:
            raise CommandError('CSV has a header but no data rows.')

        # Log first data row so we can visually confirm emoji decoded correctly.
        first = rows[0]
        self.stdout.write(
            f'\nFirst data row (visual confirmation — check emoji rendered correctly):\n'
            f'  emojis   = {first.get("emojis", "?")!r}\n'
            f'  meaning  = {first.get("meaning", "?")!r}\n'
            f'  context  = {first.get("context", "?")!r}\n'
            f'  severity = {first.get("severity", "?")!r}\n'
        )

        created = updated = skipped_admin = duplicates = 0
        singles = combos = or_sets = ambiguous = 0

        # Track (term, match_type) pairs we've processed this run, for --deactivate-missing.
        processed_pairs: set[tuple[str, str]] = set()

        with transaction.atomic():
            for row_num, row in enumerate(rows, start=2):
                raw_emojis = row.get('emojis', '').strip()
                meaning = row.get('meaning', '').strip()
                context = row.get('context', '').strip()
                raw_severity = row.get('severity', '').strip()
                notes_csv = row.get('notes', '').strip()

                if not raw_emojis:
                    self.stdout.write(self.style.WARNING(f'  Row {row_num}: empty emojis field — skipped.'))
                    continue

                match_type, patterns, is_ambiguous = classify_row(raw_emojis, meaning)
                if match_type is None:
                    self.stdout.write(
                        self.style.WARNING(f'  Row {row_num}: {raw_emojis!r} — no emoji graphemes found, skipped.')
                    )
                    continue

                severity = _map_severity(raw_severity)
                category = _map_context(context)
                notes = f'[{meaning}] {notes_csv}'.strip()

                if is_ambiguous:
                    ambiguous += 1
                    classification_label = f'COMBO (AMBIGUOUS — may be OR_SET, check in admin)'
                elif match_type == ModerationTerm.MatchType.EMOJI_COMBO:
                    classification_label = 'COMBO'
                elif match_type == ModerationTerm.MatchType.EMOJI_OR_SET:
                    classification_label = f'OR_SET ({len(patterns)} alternatives)'
                else:
                    classification_label = 'SINGLE'

                self.stdout.write(
                    f'  Row {row_num}: {raw_emojis!r} → {classification_label} | '
                    f'{severity} | {category}'
                    + (' *** AMBIGUOUS ***' if is_ambiguous else '')
                )

                for pattern in patterns:
                    if not pattern:
                        continue

                    processed_pairs.add((pattern, match_type))

                    try:
                        existing = ModerationTerm.objects.get(term=pattern, match_type=match_type)
                    except ModerationTerm.DoesNotExist:
                        existing = None

                    if existing is not None:
                        if existing.source != source:
                            skipped_admin += 1
                            self.stdout.write(
                                f'    SKIP (source={existing.source!r}): {pattern!r}'
                            )
                            continue

                        # Same pattern + match_type already exists from this source.
                        # This is a duplicate row in the file — merge the notes.
                        changed_fields = []
                        merged_notes = existing.notes
                        if notes and notes not in merged_notes:
                            merged_notes = f'{merged_notes}\n{notes}'.strip()
                            changed_fields.append('notes')
                        if existing.severity != severity:
                            existing.severity = severity
                            changed_fields.append('severity')
                        if existing.category != category:
                            existing.category = category
                            changed_fields.append('category')
                        if not existing.is_active:
                            existing.is_active = True
                            changed_fields.append('is_active')

                        if changed_fields:
                            existing.notes = merged_notes
                            if not dry_run:
                                existing.save(update_fields=changed_fields + ['notes', 'updated_at'])
                            duplicates += 1
                            self.stdout.write(
                                f'    DUPLICATE/UPDATE {pattern!r} (fields: {changed_fields})'
                            )
                        else:
                            duplicates += 1
                            self.stdout.write(f'    DUPLICATE (no change): {pattern!r}')
                        continue

                    # New row.
                    if not dry_run:
                        ModerationTerm.objects.create(
                            term=pattern,
                            match_type=match_type,
                            category=category,
                            severity=severity,
                            source=source,
                            is_active=True,
                            notes=notes,
                        )
                    created += 1

                # Tally match-type counters (once per CSV row, not per pattern).
                if match_type == ModerationTerm.MatchType.EMOJI_SINGLE:
                    singles += 1
                elif match_type == ModerationTerm.MatchType.EMOJI_COMBO:
                    combos += 1
                elif match_type == ModerationTerm.MatchType.EMOJI_OR_SET:
                    or_sets += 1

            if deactivate_missing:
                deactivated_count = 0
                for row in ModerationTerm.objects.filter(
                    source=source,
                    is_active=True,
                    match_type__in=[
                        ModerationTerm.MatchType.EMOJI_SINGLE,
                        ModerationTerm.MatchType.EMOJI_COMBO,
                        ModerationTerm.MatchType.EMOJI_OR_SET,
                    ],
                ):
                    if (row.term, row.match_type) not in processed_pairs:
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
                transaction.set_rollback(True)

        # Invalidate service cache so next request picks up new emoji rules.
        if not dry_run:
            try:
                from apps.moderation.service import ModerationService
                ModerationService.invalidate_cache()
            except Exception:
                pass

        self.stdout.write(
            self.style.SUCCESS(
                f'\nEmoji import complete.\n'
                f'  Total CSV rows:          {len(rows)}\n'
                f'  Created:                 {created}\n'
                f'  Duplicates/updated:      {duplicates}\n'
                f'  Skipped (other source):  {skipped_admin}\n'
                f'  ─── by type ───\n'
                f'  Singles (EMOJI_SINGLE):  {singles}\n'
                f'  Combos  (EMOJI_COMBO):   {combos}\n'
                f'  OR sets (EMOJI_OR_SET):  {or_sets}\n'
                f'  ─── review ────\n'
                f'  Ambiguous COMBOs:        {ambiguous}  ← check these in admin\n'
            )
        )
        if ambiguous:
            self.stdout.write(
                self.style.WARNING(
                    'ATTENTION: Ambiguous COMBO rows were imported as EMOJI_COMBO (all emojis\n'
                    'must co-occur within proximity window). If these emojis are independent\n'
                    'code words (alternatives), change match_type to EMOJI_OR_SET in the admin.\n'
                )
            )
