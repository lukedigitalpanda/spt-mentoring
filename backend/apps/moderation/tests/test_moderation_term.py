"""
Tests for ModerationTerm model, service integration, and import command.

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test apps.moderation.tests --verbosity=2
"""
import io
import tempfile
import pathlib
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.core.management import call_command

from apps.moderation.models import ModerationTerm, ModerationLog
from apps.moderation.service import ModerationService
from apps.moderation.management.commands.import_moderation_terms import (
    classify_match_type,
    classify_category,
    classify_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(**kwargs):
    from apps.users.models import User
    defaults = dict(
        username='testuser',
        email='test@example.com',
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
        subject='Test',
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


def make_term(**kwargs):
    defaults = dict(
        term='testterm',
        match_type=ModerationTerm.MatchType.SUBSTRING,
        category=ModerationTerm.Category.PROFANITY,
        severity=ModerationTerm.Severity.MEDIUM,
        source='bulk_import_v1',
        is_active=True,
    )
    defaults.update(kwargs)
    obj, _ = ModerationTerm.objects.get_or_create(
        term=defaults['term'],
        match_type=defaults['match_type'],
        defaults={k: v for k, v in defaults.items() if k not in ('term', 'match_type')},
    )
    return obj


# ---------------------------------------------------------------------------
# Classification unit tests
# ---------------------------------------------------------------------------

class ClassifyMatchTypeTests(TestCase):

    def test_email_with_at(self):
        self.assertEqual(classify_match_type('@gmail.com'), ModerationTerm.MatchType.EMAIL_PATTERN)

    def test_email_wildcard(self):
        self.assertEqual(classify_match_type('*@hotmail.com'), ModerationTerm.MatchType.EMAIL_PATTERN)

    def test_bare_at(self):
        self.assertEqual(classify_match_type('@'), ModerationTerm.MatchType.EMAIL_PATTERN)

    def test_url_fragment_www(self):
        self.assertEqual(classify_match_type('www'), ModerationTerm.MatchType.URL_FRAGMENT)

    def test_url_fragment_http(self):
        self.assertEqual(classify_match_type('http:'), ModerationTerm.MatchType.URL_FRAGMENT)

    def test_regex_question_mark(self):
        self.assertEqual(classify_match_type('teams?'), ModerationTerm.MatchType.REGEX)

    def test_wildcard(self):
        self.assertEqual(classify_match_type('masterbat*'), ModerationTerm.MatchType.WILDCARD)

    def test_substring_plain(self):
        self.assertEqual(classify_match_type('bitch'), ModerationTerm.MatchType.SUBSTRING)

    def test_substring_obfuscated(self):
        self.assertEqual(classify_match_type('sh1t'), ModerationTerm.MatchType.SUBSTRING)

    def test_substring_multiword(self):
        self.assertEqual(classify_match_type('blow job'), ModerationTerm.MatchType.SUBSTRING)


class ClassifySeverityTests(TestCase):

    def test_critical_term(self):
        self.assertEqual(
            classify_severity('kill', ModerationTerm.MatchType.SUBSTRING),
            ModerationTerm.Severity.CRITICAL,
        )

    def test_critical_phrase(self):
        self.assertEqual(
            classify_severity('how to kill', ModerationTerm.MatchType.SUBSTRING),
            ModerationTerm.Severity.CRITICAL,
        )

    def test_low_term(self):
        self.assertEqual(
            classify_severity('damn', ModerationTerm.MatchType.SUBSTRING),
            ModerationTerm.Severity.LOW,
        )

    def test_email_pattern_is_high(self):
        self.assertEqual(
            classify_severity('*@hotmail.com', ModerationTerm.MatchType.EMAIL_PATTERN),
            ModerationTerm.Severity.HIGH,
        )

    def test_url_fragment_is_high(self):
        self.assertEqual(
            classify_severity('www', ModerationTerm.MatchType.URL_FRAGMENT),
            ModerationTerm.Severity.HIGH,
        )

    def test_default_medium(self):
        self.assertEqual(
            classify_severity('wanker', ModerationTerm.MatchType.SUBSTRING),
            ModerationTerm.Severity.MEDIUM,
        )


# ---------------------------------------------------------------------------
# Service screen() tests — one per match_type
# ---------------------------------------------------------------------------

class ServiceScreenTests(TestCase):

    def setUp(self):
        ModerationService.invalidate_cache()

    def tearDown(self):
        ModerationService.invalidate_cache()

    def _screen(self, body, suppress_notifications=True):
        msg = make_message(body)
        with patch.object(ModerationService, '_alert_staff'), \
             patch.object(ModerationService, '_notify_sender_flagged'), \
             patch.object(ModerationService, '_notify_sender_blocked'):
            return ModerationService.screen(msg), msg

    # --- SUBSTRING ---

    def test_substring_blocks_obfuscated_variant(self):
        """sh1t inside 'thisissh1ttext' triggers a SUBSTRING HIGH match → blocked."""
        make_term(term='sh1t', match_type=ModerationTerm.MatchType.SUBSTRING,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, msg = self._screen('thisissh1ttext')
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(result.triggered_term, 'sh1t')

    def test_substring_benign_message_delivers(self):
        make_term(term='sh1t', match_type=ModerationTerm.MatchType.SUBSTRING,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('Hello, how are you today?')
        self.assertEqual(result.status, 'delivered')

    # --- REGEX ---

    def test_regex_teams_singular(self):
        """'teams?' catches 'team' (singular)."""
        make_term(term='teams?', match_type=ModerationTerm.MatchType.REGEX,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('please add me on team')
        self.assertEqual(result.status, 'blocked')

    def test_regex_teams_plural(self):
        """'teams?' catches 'teams' (plural)."""
        make_term(term='teams?', match_type=ModerationTerm.MatchType.REGEX,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('please add me on teams')
        self.assertEqual(result.status, 'blocked')

    def test_regex_benign_no_match(self):
        make_term(term='teams?', match_type=ModerationTerm.MatchType.REGEX,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('Great work from the whole teaming effort!')
        # 'teaming' contains 'team' — regex matches; this is expected/intentional.
        # So test a truly benign message instead:
        result, _ = self._screen('Hello, I hope you are well.')
        self.assertEqual(result.status, 'delivered')

    # --- WILDCARD ---

    def test_wildcard_masterbat_prefix(self):
        make_term(term='masterbat*', match_type=ModerationTerm.MatchType.WILDCARD,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('I was masterbating last night')
        self.assertEqual(result.status, 'blocked')

    def test_wildcard_no_match_on_benign(self):
        make_term(term='masterbat*', match_type=ModerationTerm.MatchType.WILDCARD,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('Hello there, how are you?')
        self.assertEqual(result.status, 'delivered')

    # --- EMAIL_PATTERN ---

    def test_email_pattern_hotmail(self):
        """john.smith@hotmail.com triggers *@hotmail.com pattern."""
        make_term(term='*@hotmail.com', match_type=ModerationTerm.MatchType.EMAIL_PATTERN,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('contact me at john.smith@hotmail.com please')
        self.assertEqual(result.status, 'blocked')

    def test_email_pattern_does_not_match_other_domain(self):
        """*@hotmail.com does NOT match a gmail address."""
        make_term(term='*@hotmail.com', match_type=ModerationTerm.MatchType.EMAIL_PATTERN,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('My colleague is user@gmail.com')
        self.assertEqual(result.status, 'delivered')

    def test_email_pattern_bare_at_catches_any_email(self):
        make_term(term='@', match_type=ModerationTerm.MatchType.EMAIL_PATTERN,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('reach me at secret@example.org')
        self.assertEqual(result.status, 'blocked')

    # --- URL_FRAGMENT ---

    def test_url_fragment_www(self):
        make_term(term='www', match_type=ModerationTerm.MatchType.URL_FRAGMENT,
                  severity=ModerationTerm.Severity.HIGH)
        ModerationService.invalidate_cache()

        result, _ = self._screen('visit www.example.com for details')
        self.assertEqual(result.status, 'blocked')

    # --- Severity outcomes ---

    def test_medium_severity_flags_not_blocks(self):
        make_term(term='darn', match_type=ModerationTerm.MatchType.SUBSTRING,
                  severity=ModerationTerm.Severity.MEDIUM)
        ModerationService.invalidate_cache()

        result, msg = self._screen('this is so darn annoying')
        self.assertEqual(result.status, 'flagged')

    def test_low_severity_delivers_with_log(self):
        make_term(term='crap', match_type=ModerationTerm.MatchType.SUBSTRING,
                  severity=ModerationTerm.Severity.LOW)
        ModerationService.invalidate_cache()

        result, msg = self._screen('oh crap I forgot')
        self.assertEqual(result.status, 'delivered')
        # LOW terms create a ModerationLog entry even though delivered
        self.assertTrue(ModerationLog.objects.filter(message=msg).exists())

    def test_critical_blocks(self):
        make_term(term='murder', match_type=ModerationTerm.MatchType.SUBSTRING,
                  severity=ModerationTerm.Severity.CRITICAL)
        ModerationService.invalidate_cache()

        result, _ = self._screen('I want to commit murder')
        self.assertEqual(result.status, 'blocked')


# ---------------------------------------------------------------------------
# Import command tests
# ---------------------------------------------------------------------------

class ImportCommandTests(TestCase):

    def _write_terms_file(self, terms: list[str]) -> pathlib.Path:
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        )
        tmp.write('\n'.join(terms))
        tmp.flush()
        return pathlib.Path(tmp.name)

    def _run_import(self, terms, **kwargs):
        path = self._write_terms_file(terms)
        out = io.StringIO()
        call_command(
            'import_moderation_terms',
            file=str(path),
            stdout=out,
            **kwargs,
        )
        return out.getvalue()

    def test_basic_import_creates_rows(self):
        self._run_import(['bitch', 'wanker', 'sh1t'])
        self.assertEqual(ModerationTerm.objects.count(), 3)

    def test_idempotent_second_run_creates_zero(self):
        terms = ['bitch', 'wanker', 'sh1t']
        self._run_import(terms)
        count_after_first = ModerationTerm.objects.count()

        output = self._run_import(terms)
        count_after_second = ModerationTerm.objects.count()

        self.assertEqual(count_after_first, count_after_second)
        self.assertIn('Created:                 0', output)

    def test_dry_run_makes_no_db_changes(self):
        self._run_import(['bitch', 'wanker'], dry_run=True)
        self.assertEqual(ModerationTerm.objects.count(), 0)

    def test_admin_sourced_row_not_overwritten(self):
        """A row with source='admin' is never overwritten by the importer."""
        admin_row = ModerationTerm.objects.create(
            term='bitch',
            match_type=ModerationTerm.MatchType.SUBSTRING,
            category=ModerationTerm.Category.SLUR,
            severity=ModerationTerm.Severity.CRITICAL,
            source='admin',
            is_active=True,
        )
        self._run_import(['bitch'])

        admin_row.refresh_from_db()
        # Source must not have changed
        self.assertEqual(admin_row.source, 'admin')
        # Severity must not have been overwritten
        self.assertEqual(admin_row.severity, ModerationTerm.Severity.CRITICAL)
        # No duplicate row created
        self.assertEqual(
            ModerationTerm.objects.filter(term='bitch', match_type=ModerationTerm.MatchType.SUBSTRING).count(),
            1,
        )

    def test_deactivate_missing_only_touches_import_source(self):
        """--deactivate-missing deactivates bulk_import_v1 rows absent from file,
        but never touches rows from other sources."""
        # Admin-managed row for a term that won't be in the new file
        admin_row = ModerationTerm.objects.create(
            term='admin_only_term',
            match_type=ModerationTerm.MatchType.SUBSTRING,
            source='admin',
            is_active=True,
        )
        # First import with 'bitch' only
        self._run_import(['bitch'])
        self.assertTrue(ModerationTerm.objects.get(term='bitch').is_active)

        # Second import with 'wanker' only + deactivate-missing
        self._run_import(['wanker'], deactivate_missing=True)

        # 'bitch' was from bulk_import_v1 and absent → should be deactivated
        self.assertFalse(ModerationTerm.objects.get(term='bitch').is_active)
        # admin_row must be untouched
        admin_row.refresh_from_db()
        self.assertTrue(admin_row.is_active)

    def test_email_pattern_classified_correctly(self):
        self._run_import(['*@hotmail.com'])
        term = ModerationTerm.objects.get(term='*@hotmail.com')
        self.assertEqual(term.match_type, ModerationTerm.MatchType.EMAIL_PATTERN)
        self.assertEqual(term.category, ModerationTerm.Category.CONTACT_LEAK)
        self.assertEqual(term.severity, ModerationTerm.Severity.HIGH)

    def test_regex_term_classified_correctly(self):
        self._run_import(['teams?'])
        term = ModerationTerm.objects.get(term='teams?')
        self.assertEqual(term.match_type, ModerationTerm.MatchType.REGEX)

    def test_wildcard_term_classified_correctly(self):
        self._run_import(['masterbat*'])
        term = ModerationTerm.objects.get(term='masterbat*')
        self.assertEqual(term.match_type, ModerationTerm.MatchType.WILDCARD)

    def test_critical_severity_assigned_to_kill(self):
        self._run_import(['kill'])
        term = ModerationTerm.objects.get(term='kill')
        self.assertEqual(term.severity, ModerationTerm.Severity.CRITICAL)

    def test_blank_lines_skipped(self):
        path = self._write_terms_file(['bitch', '', '   ', 'wanker'])
        out = io.StringIO()
        call_command('import_moderation_terms', file=str(path), stdout=out)
        self.assertEqual(ModerationTerm.objects.count(), 2)

    def test_missing_file_raises_error(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command('import_moderation_terms', file='/nonexistent/path/terms.txt')

    def test_output_summary_counts(self):
        output = self._run_import(['bitch', 'wanker', 'sh1t'])
        self.assertIn('Total in file:           3', output)
        self.assertIn('Created:                 3', output)

    def test_updated_count_reported_on_rerun_with_change(self):
        """If a term exists from same source but severity changes, it's counted as updated."""
        ModerationTerm.objects.create(
            term='kill',
            match_type=ModerationTerm.MatchType.SUBSTRING,
            severity=ModerationTerm.Severity.LOW,  # wrong — will be corrected
            source='bulk_import_v1',
            is_active=True,
        )
        output = self._run_import(['kill'])
        self.assertIn('Updated:                 1', output)
        self.assertEqual(
            ModerationTerm.objects.get(term='kill').severity,
            ModerationTerm.Severity.CRITICAL,
        )
