"""
Tests for the emoji moderation layer.

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test \
        apps.moderation.tests.test_emoji_moderation --verbosity=2

Coverage:
  - grapheme helper functions (utils/emoji.py)
  - compute_score() scoring function
  - _combo_fires() proximity check
  - ModerationService.screen() with emoji rules
  - import_emoji_terms management command
"""
import io
import tempfile
import pathlib

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.management import call_command

from apps.moderation.models import ModerationTerm, ModerationLog
from apps.moderation.service import ModerationService, compute_score, _combo_fires
from apps.moderation.utils.emoji import (
    extract_emoji_graphemes,
    normalise_emoji,
    normalise_emoji_sequence,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(**kwargs):
    from apps.users.models import User
    defaults = dict(
        username='testuser_emoji',
        email='emoji_test@example.com',
        first_name='Test',
        last_name='User',
        role=User.Role.MENTOR,
        is_active=True,
        is_verified=True,
        notification_email=False,
    )
    defaults.update(kwargs)
    user, _ = User.objects.get_or_create(email=defaults['email'], defaults=defaults)
    return user


def make_conversation(participants=None):
    from apps.messaging.models import Conversation
    conv = Conversation.objects.create(
        conversation_type='direct',
        subject='Emoji Test',
        is_private=True,
    )
    if participants:
        conv.participants.set(participants)
    return conv


def make_message(body, sender=None, conversation=None):
    from apps.messaging.models import Message
    if sender is None:
        sender = make_user()
    if conversation is None:
        conversation = make_conversation(participants=[sender])
    return Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=body,
        status=Message.Status.PENDING,
    )


def make_emoji_term(term, match_type, severity=ModerationTerm.Severity.MEDIUM,
                    category=ModerationTerm.Category.SEXUAL, source='emoji_bulk_v1'):
    obj, _ = ModerationTerm.objects.get_or_create(
        term=term,
        match_type=match_type,
        defaults={
            'severity': severity,
            'category': category,
            'source': source,
            'is_active': True,
        },
    )
    return obj


# ---------------------------------------------------------------------------
# Grapheme helper unit tests
# ---------------------------------------------------------------------------

class ExtractEmojiGraphemesTests(TestCase):

    def test_plain_aubergine(self):
        result = extract_emoji_graphemes('🍆')
        self.assertEqual(result, ['🍆'])

    def test_message_with_text_and_emoji(self):
        result = extract_emoji_graphemes('hello 🍆 world')
        self.assertEqual(result, ['🍆'])

    def test_multiple_emoji(self):
        result = extract_emoji_graphemes('🍆🍑')
        self.assertEqual(len(result), 2)
        self.assertIn('🍆', result)
        self.assertIn('🍑', result)

    def test_pure_text_returns_empty(self):
        result = extract_emoji_graphemes('just some words')
        self.assertEqual(result, [])

    def test_fire_emoji(self):
        result = extract_emoji_graphemes('🔥')
        self.assertEqual(result, ['🔥'])

    def test_snowflake_with_variation_selector(self):
        # ❄️ = U+2744 + U+FE0F — one grapheme cluster
        result = extract_emoji_graphemes('❄️')
        self.assertEqual(len(result), 1)


class NormaliseEmojiTests(TestCase):

    def test_plain_aubergine_unchanged(self):
        self.assertEqual(normalise_emoji('🍆'), '🍆')

    def test_fire_unchanged(self):
        self.assertEqual(normalise_emoji('🔥'), '🔥')

    def test_skin_tone_stripped(self):
        # 🍆 + dark skin tone modifier → should strip modifier → 🍆
        # (In practice, 🍆 doesn't have a skin-tone variant, but we test the
        #  stripping logic using a cluster that does: 👋🏿 → 👋)
        cluster = '👋\U0001F3FF'  # waving hand + dark skin tone
        result = normalise_emoji(cluster)
        self.assertEqual(result, '👋')

    def test_variation_selector_stripped(self):
        # ❄️ = snowflake + U+FE0F variation selector
        cluster = '❄️'
        result = normalise_emoji(cluster)
        self.assertEqual(result, '❄')

    def test_zwj_sequence_preserved(self):
        # 👨‍💻 = man + ZWJ + laptop — ZWJ must be kept
        cluster = '👨‍💻'
        result = normalise_emoji(cluster)
        self.assertIn('‍', result)
        self.assertIn('👨', result)


class NormaliseEmojiSequenceTests(TestCase):

    def test_plain_aubergine(self):
        self.assertEqual(normalise_emoji_sequence('🍆'), '🍆')

    def test_text_discarded(self):
        self.assertEqual(normalise_emoji_sequence('hello 🍆 world'), '🍆')

    def test_combo_preserved(self):
        result = normalise_emoji_sequence('🍆🍑')
        self.assertIn('🍆', result)
        self.assertIn('🍑', result)
        self.assertEqual(len(extract_emoji_graphemes(result)), 2)

    def test_skin_tone_stripped_in_sequence(self):
        # 🍆🏻 — aubergine followed by light skin-tone modifier
        # Skin tone modifiers attach to the preceding emoji as one grapheme cluster
        import grapheme as _grapheme
        import emoji as _emoji
        # Build: aubergine + light skin tone (forms one grapheme cluster if valid)
        cluster_with_tone = '🍆\U0001F3FB'
        clusters = list(_grapheme.graphemes(cluster_with_tone))
        # The result of normalise_emoji_sequence should be just 🍆
        result = normalise_emoji_sequence(cluster_with_tone)
        self.assertIn('🍆', result)
        self.assertNotIn('\U0001F3FB', result)

    def test_empty_string(self):
        self.assertEqual(normalise_emoji_sequence(''), '')

    def test_no_emoji_returns_empty(self):
        self.assertEqual(normalise_emoji_sequence('hello world'), '')


# ---------------------------------------------------------------------------
# Scoring unit tests
# ---------------------------------------------------------------------------

class ComputeScoreTests(TestCase):

    def _hit(self, match_type, severity, source='emoji'):
        return {'match_type': match_type, 'severity': severity, 'source': source}

    def test_critical_text_rule(self):
        hits = [self._hit('text', ModerationTerm.Severity.CRITICAL, source='text')]
        self.assertEqual(compute_score(hits, []), 100)

    def test_high_text_rule(self):
        hits = [self._hit('text', ModerationTerm.Severity.HIGH, source='text')]
        self.assertEqual(compute_score(hits, []), 80)

    def test_medium_text_rule(self):
        hits = [self._hit('text', ModerationTerm.Severity.MEDIUM, source='text')]
        self.assertEqual(compute_score(hits, []), 50)

    def test_low_text_rule(self):
        hits = [self._hit('text', ModerationTerm.Severity.LOW, source='text')]
        self.assertEqual(compute_score(hits, []), 20)

    def test_emoji_single_high(self):
        hits = [self._hit(ModerationTerm.MatchType.EMOJI_SINGLE, ModerationTerm.Severity.HIGH)]
        self.assertEqual(compute_score([], hits), 30)

    def test_emoji_single_medium(self):
        hits = [self._hit(ModerationTerm.MatchType.EMOJI_SINGLE, ModerationTerm.Severity.MEDIUM)]
        self.assertEqual(compute_score([], hits), 15)

    def test_emoji_single_low(self):
        hits = [self._hit(ModerationTerm.MatchType.EMOJI_SINGLE, ModerationTerm.Severity.LOW)]
        self.assertEqual(compute_score([], hits), 5)

    def test_emoji_combo_high(self):
        hits = [self._hit(ModerationTerm.MatchType.EMOJI_COMBO, ModerationTerm.Severity.HIGH)]
        self.assertEqual(compute_score([], hits), 80)

    def test_emoji_combo_medium(self):
        hits = [self._hit(ModerationTerm.MatchType.EMOJI_COMBO, ModerationTerm.Severity.MEDIUM)]
        self.assertEqual(compute_score([], hits), 50)

    def test_emoji_or_set_high(self):
        hits = [self._hit(ModerationTerm.MatchType.EMOJI_OR_SET, ModerationTerm.Severity.HIGH)]
        self.assertEqual(compute_score([], hits), 60)

    def test_cross_signal_boost(self):
        text_hit = [self._hit('text', ModerationTerm.Severity.LOW, source='text')]
        emoji_hit = [self._hit(ModerationTerm.MatchType.EMOJI_SINGLE, ModerationTerm.Severity.LOW)]
        # LOW text (20) + SINGLE LOW (5) + boost (20) = 45
        self.assertEqual(compute_score(text_hit, emoji_hit), 45)

    def test_no_cross_boost_without_text(self):
        emoji_hit = [self._hit(ModerationTerm.MatchType.EMOJI_SINGLE, ModerationTerm.Severity.LOW)]
        self.assertEqual(compute_score([], emoji_hit), 5)


# ---------------------------------------------------------------------------
# Proximity check unit tests
# ---------------------------------------------------------------------------

class ComboFiresTests(TestCase):

    def test_two_adjacent_emojis(self):
        self.assertTrue(_combo_fires(['🍆', '🍑'], ['🍆', '🍑'], proximity=10))

    def test_two_far_apart_emojis_outside_window(self):
        # 15 emojis apart — outside proximity window of 10
        emojis = ['🍆'] + ['🔥'] * 14 + ['🍑']
        self.assertFalse(_combo_fires(emojis, ['🍆', '🍑'], proximity=10))

    def test_two_emojis_exactly_at_boundary(self):
        # 10 positions apart — exactly at the limit
        emojis = ['🍆'] + ['🔥'] * 9 + ['🍑']
        self.assertTrue(_combo_fires(emojis, ['🍆', '🍑'], proximity=10))

    def test_missing_part_returns_false(self):
        self.assertFalse(_combo_fires(['🍆', '🔥'], ['🍆', '🍑'], proximity=10))

    def test_three_part_combo_all_close(self):
        emojis = ['💦', '😮', '😛']
        self.assertTrue(_combo_fires(emojis, ['💦', '😮', '😛'], proximity=10))

    def test_three_part_combo_one_too_far(self):
        emojis = ['💦'] + ['🔥'] * 11 + ['😮', '😛']
        self.assertFalse(_combo_fires(emojis, ['💦', '😮', '😛'], proximity=10))

    def test_empty_combo_parts(self):
        self.assertFalse(_combo_fires(['🍆'], [], proximity=10))


# ---------------------------------------------------------------------------
# ModerationService screen() integration tests
# ---------------------------------------------------------------------------

class EmojiScreenTests(TestCase):

    def setUp(self):
        ModerationService.invalidate_cache()
        # Suppress actual email/notification side-effects.
        self._patches = [
            patch('apps.moderation.service.ModerationService._alert_staff'),
            patch('apps.moderation.service.ModerationService._notify_sender_flagged'),
            patch('apps.moderation.service.ModerationService._notify_sender_blocked'),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        ModerationService.invalidate_cache()

    # --- Single emoji: flagged but NOT blocked ---

    def test_single_aubergine_not_blocked(self):
        """🍆 alone → score ~15 (MEDIUM SINGLE) → delivered, not blocked."""
        make_emoji_term('🍆', ModerationTerm.MatchType.EMOJI_SINGLE,
                        severity=ModerationTerm.Severity.MEDIUM)
        ModerationService.invalidate_cache()

        msg = make_message('hey 🍆')
        result = ModerationService.screen(msg)

        self.assertEqual(result.status, 'delivered')
        self.assertLess(result.score, 50)
        self.assertTrue(result.single_emoji_only)
        self.assertTrue(result.emoji_only_hit)

    # --- Combo: blocked ---

    def test_aubergine_peach_combo_blocked(self):
        """🍆🍑 together → score 80 (HIGH COMBO) → blocked."""
        make_emoji_term('🍆🍑', ModerationTerm.MatchType.EMOJI_COMBO,
                        severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        msg = make_message('check this 🍆🍑')
        result = ModerationService.screen(msg)

        self.assertEqual(result.status, 'blocked')
        self.assertGreaterEqual(result.score, 80)

    # --- Single fire emoji: audit log only ---

    def test_fire_alone_audit_only(self):
        """🔥 alone → score 5 (LOW SINGLE) → delivered, no flag."""
        make_emoji_term('🔥', ModerationTerm.MatchType.EMOJI_SINGLE,
                        severity=ModerationTerm.Severity.LOW,
                        category=ModerationTerm.Category.DRUGS_ALCOHOL)
        ModerationService.invalidate_cache()

        msg = make_message('this is 🔥 content')
        result = ModerationService.screen(msg)

        self.assertEqual(result.status, 'delivered')
        self.assertEqual(result.score, 5)

    # --- Cross-signal boost: text + emoji ---

    def test_fire_plus_weed_text_boosts_score(self):
        """🔥 + 'weed' text → text LOW (20) + emoji LOW (5) + boost (20) = 45 → delivered+review."""
        make_emoji_term('🔥', ModerationTerm.MatchType.EMOJI_SINGLE,
                        severity=ModerationTerm.Severity.LOW,
                        category=ModerationTerm.Category.DRUGS_ALCOHOL)
        ModerationTerm.objects.get_or_create(
            term='weed',
            match_type=ModerationTerm.MatchType.SUBSTRING,
            defaults={
                'severity': ModerationTerm.Severity.LOW,
                'category': ModerationTerm.Category.DRUGS_ALCOHOL,
                'source': 'test',
                'is_active': True,
            },
        )
        ModerationService.invalidate_cache()

        msg = make_message('🔥 got some weed')
        result = ModerationService.screen(msg)

        self.assertEqual(result.status, 'delivered')
        self.assertEqual(result.score, 45)
        self.assertFalse(result.emoji_only_hit)

    # --- Skin-tone normalisation ---

    def test_skin_tone_variant_matches_plain_rule(self):
        """🍆🏻 (aubergine + light skin tone) should match the 🍆 SINGLE rule."""
        make_emoji_term('🍆', ModerationTerm.MatchType.EMOJI_SINGLE,
                        severity=ModerationTerm.Severity.MEDIUM)
        ModerationService.invalidate_cache()

        aubergine_with_tone = '🍆\U0001F3FB'
        msg = make_message(f'hello {aubergine_with_tone}')
        result = ModerationService.screen(msg)

        # Should find the emoji (score > 0)
        self.assertGreater(result.score, 0)
        self.assertIn('🍆', result.triggered_term)

    # --- Combo proximity: too far apart does NOT fire ---

    def test_combo_emojis_far_apart_do_not_fire(self):
        """🍆 and 🍑 separated by 15+ other emoji → COMBO does NOT fire."""
        make_emoji_term('🍆🍑', ModerationTerm.MatchType.EMOJI_COMBO,
                        severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        filler = '🔥' * 15
        msg = make_message(f'🍆 {filler} 🍑')
        result = ModerationService.screen(msg)

        self.assertNotEqual(result.status, 'blocked')
        self.assertEqual(result.score, 0)

    # --- OR set: snowflake alone → flagged (score 60) ---

    def test_or_set_single_member_fires(self):
        """❄ alone in a message → EMOJI_OR_SET HIGH fires → score 60 → flagged."""
        # Normalise ❄️ → ❄ (strip variation selector)
        snowflake = normalise_emoji('❄️')
        make_emoji_term(snowflake, ModerationTerm.MatchType.EMOJI_OR_SET,
                        severity=ModerationTerm.Severity.HIGH,
                        category=ModerationTerm.Category.DRUGS_ALCOHOL)
        ModerationService.invalidate_cache()

        msg = make_message('cold weather ❄️ today')
        result = ModerationService.screen(msg)

        self.assertEqual(result.status, 'flagged')
        self.assertEqual(result.score, 60)
        self.assertTrue(result.emoji_only_hit)

    # --- Admin-sourced rule is not overwritten by importer ---

    def test_admin_sourced_rule_preserved_on_reimport(self):
        """A rule with source='admin' must not be touched by the importer."""
        admin_rule = make_emoji_term(
            '🍆', ModerationTerm.MatchType.EMOJI_SINGLE,
            source='admin',
            severity=ModerationTerm.Severity.CRITICAL,
        )
        original_severity = admin_rule.severity

        csv_content = 'emojis,meaning,context,severity,notes\n🍆,Test,Sexting,LOW,test\n'
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', encoding='utf-8', delete=False
        ) as f:
            f.write(csv_content)
            tmp_path = f.name

        call_command('import_emoji_terms', file=tmp_path, source='emoji_bulk_v1', verbosity=0)

        admin_rule.refresh_from_db()
        self.assertEqual(admin_rule.severity, original_severity)
        self.assertEqual(admin_rule.source, 'admin')

    # --- Dry run makes no DB changes ---

    def test_dry_run_no_db_changes(self):
        """--dry-run must not create or modify any rows."""
        count_before = ModerationTerm.objects.filter(
            match_type=ModerationTerm.MatchType.EMOJI_SINGLE
        ).count()

        csv_content = 'emojis,meaning,context,severity,notes\n🍆,Test,Sexting,MEDIUM,test\n'
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', encoding='utf-8', delete=False
        ) as f:
            f.write(csv_content)
            tmp_path = f.name

        call_command(
            'import_emoji_terms',
            file=tmp_path,
            dry_run=True,
            source='emoji_bulk_v1',
            verbosity=0,
        )

        count_after = ModerationTerm.objects.filter(
            match_type=ModerationTerm.MatchType.EMOJI_SINGLE
        ).count()
        self.assertEqual(count_before, count_after)

    # --- Idempotent: second import → 0 creates ---

    def test_idempotent_second_import(self):
        """Running the import twice produces 0 creates on the second run."""
        csv_content = 'emojis,meaning,context,severity,notes\n🌿,Cannabis,Drug selling/buying online,MEDIUM,herb\n'
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', encoding='utf-8', delete=False
        ) as f:
            f.write(csv_content)
            tmp_path = f.name

        out1 = io.StringIO()
        call_command('import_emoji_terms', file=tmp_path, source='emoji_bulk_v1', stdout=out1, verbosity=1)

        out2 = io.StringIO()
        call_command('import_emoji_terms', file=tmp_path, source='emoji_bulk_v1', stdout=out2, verbosity=1)

        # On second run, Created should be 0
        output2 = out2.getvalue()
        self.assertIn('Created:                 0', output2)


# ---------------------------------------------------------------------------
# Import command classification tests
# ---------------------------------------------------------------------------

class ImportClassificationTests(TestCase):

    def setUp(self):
        ModerationService.invalidate_cache()

    def tearDown(self):
        ModerationService.invalidate_cache()

    def _run_import(self, csv_body: str, **kwargs):
        full_csv = f'emojis,meaning,context,severity,notes\n{csv_body}'
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', encoding='utf-8', delete=False
        ) as f:
            f.write(full_csv)
            tmp_path = f.name
        out = io.StringIO()
        call_command(
            'import_emoji_terms',
            file=tmp_path,
            source='test_source',
            stdout=out,
            verbosity=1,
            **kwargs,
        )
        return out.getvalue()

    def test_single_emoji_creates_single_rule(self):
        self._run_import('🔥,Fire,Drug selling/buying online,LOW,test')
        self.assertEqual(
            ModerationTerm.objects.filter(
                term__contains='🔥',
                match_type=ModerationTerm.MatchType.EMOJI_SINGLE,
                source='test_source',
            ).count(),
            1,
        )

    def test_combo_no_slash_creates_combo_rule(self):
        self._run_import('🍆🍑,Anal sex,Sexting,HIGH,test')
        self.assertEqual(
            ModerationTerm.objects.filter(
                match_type=ModerationTerm.MatchType.EMOJI_COMBO,
                source='test_source',
            ).count(),
            1,
        )

    def test_or_set_slash_creates_multiple_single_rules(self):
        """💵💯 with slash in meaning → 2 separate EMOJI_OR_SET rows."""
        self._run_import("💵💯,'Go for it' / consent,Sexting,MEDIUM,test")
        self.assertEqual(
            ModerationTerm.objects.filter(
                match_type=ModerationTerm.MatchType.EMOJI_OR_SET,
                source='test_source',
            ).count(),
            2,
        )

    def test_bom_stripped(self):
        """CSV with BOM should import cleanly."""
        csv_with_bom = '﻿emojis,meaning,context,severity,notes\n🔥,Fire,Drug selling/buying online,LOW,test\n'
        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.csv', delete=False
        ) as f:
            f.write(csv_with_bom.encode('utf-8'))
            tmp_path = f.name
        out = io.StringIO()
        call_command(
            'import_emoji_terms',
            file=tmp_path,
            source='test_bom',
            stdout=out,
            verbosity=1,
        )
        self.assertEqual(
            ModerationTerm.objects.filter(source='test_bom').count(), 1
        )

    def test_duplicate_emoji_rows_merged(self):
        """👀 appears twice → only one DB row created (notes merged)."""
        csv_body = (
            '👀,Parents watching,Parent/carer involvement / digital penetration,LOW,first meaning\n'
            '👀,Use of drugs,Drug selling/buying online,LOW,second meaning\n'
        )
        self._run_import(csv_body)
        rows = ModerationTerm.objects.filter(
            term__contains='👀',
            source='test_source',
        )
        self.assertEqual(rows.count(), 1)
        row = rows.first()
        self.assertIn('first meaning', row.notes)
        self.assertIn('second meaning', row.notes)

    def test_ambiguous_combo_flagged_in_output(self):
        """Cocaine row (❄️🥛⚪🎱) should be classified COMBO and flagged AMBIGUOUS."""
        output = self._run_import('❄️🥛⚪🎱,Cocaine,Drug selling/buying online,HIGH,test')
        self.assertIn('AMBIGUOUS', output)

    def test_non_utf8_file_raises_error(self):
        """A Latin-1-encoded file should raise CommandError, not silently mangle data."""
        from django.core.management.base import CommandError
        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.csv', delete=False
        ) as f:
            f.write(b'emojis,meaning,context,severity,notes\n\xff\xfe,bad,bad,LOW,bad\n')
            tmp_path = f.name
        with self.assertRaises(CommandError):
            call_command('import_emoji_terms', file=tmp_path, verbosity=0)
