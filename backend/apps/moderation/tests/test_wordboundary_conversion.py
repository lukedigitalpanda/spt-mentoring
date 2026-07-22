"""
Tests for the plain-letter -> word-boundary moderation conversion.

Background (2026-06-30): 968 plain-letter terms were imported with
match_type=SUBSTRING, so short terms matched *inside* innocent words
('af' in afternoon, 'tit' in title, 'kill' in skills, 'anal' in analysis).
The `convert_plain_substring_terms` command flips plain alphabetic SUBSTRING
terms to EXACT (word-boundary) matching, while leaving obfuscated terms
(containing digits/symbols, e.g. '5h1t', 'a$$') as SUBSTRING so evasion is
still caught.

Run with:
    docker exec spt-mentoring-backend-1 python manage.py test apps.moderation.tests --verbosity=2
"""
from django.test import TestCase
from django.core.management import call_command

from apps.moderation.models import ModerationTerm
from apps.moderation.service import ModerationService


def make_term(term, severity=ModerationTerm.Severity.MEDIUM,
              match_type=ModerationTerm.MatchType.SUBSTRING,
              category=ModerationTerm.Category.PROFANITY):
    obj, _ = ModerationTerm.objects.get_or_create(
        term=term,
        match_type=match_type,
        defaults=dict(severity=severity, category=category,
                      source='bulk_import_v1', is_active=True),
    )
    return obj


class ConvertCommandUnitTests(TestCase):
    def test_plain_term_becomes_exact_obfuscated_stays_substring(self):
        plain = make_term('tit')
        leet = make_term('5h1t')
        multiword = make_term('blow job')  # contains a space -> not plain alpha

        call_command('convert_plain_substring_terms')

        plain.refresh_from_db()
        leet.refresh_from_db()
        multiword.refresh_from_db()
        self.assertEqual(plain.match_type, ModerationTerm.MatchType.EXACT)
        self.assertEqual(leet.match_type, ModerationTerm.MatchType.SUBSTRING)
        self.assertEqual(multiword.match_type, ModerationTerm.MatchType.SUBSTRING)

    def test_dry_run_changes_nothing(self):
        plain = make_term('tit')
        call_command('convert_plain_substring_terms', '--dry-run')
        plain.refresh_from_db()
        self.assertEqual(plain.match_type, ModerationTerm.MatchType.SUBSTRING)


class ScreeningAfterConversionTests(TestCase):
    """End-to-end: seed prod-like SUBSTRING terms, convert, then screen text."""

    def setUp(self):
        make_term('af', severity=ModerationTerm.Severity.MEDIUM)
        make_term('tit', severity=ModerationTerm.Severity.MEDIUM)
        make_term('spac', severity=ModerationTerm.Severity.MEDIUM)
        make_term('kill', severity=ModerationTerm.Severity.CRITICAL,
                  category=ModerationTerm.Category.SAFEGUARDING)
        make_term('anal', severity=ModerationTerm.Severity.HIGH)
        make_term('5h1t', severity=ModerationTerm.Severity.MEDIUM)  # obfuscated
        call_command('convert_plain_substring_terms')
        ModerationService.invalidate_cache()

    def tearDown(self):
        ModerationService.invalidate_cache()

    def _status(self, body):
        return ModerationService.screen_text(body).status

    # --- innocent words no longer trip (the reported regressions) ---
    def test_afternoon_delivers(self):
        self.assertEqual(self._status("Let's meet this afternoon"), 'delivered')

    def test_title_delivers(self):
        self.assertEqual(self._status('What is the title of your project?'), 'delivered')

    def test_space_delivers(self):
        self.assertEqual(self._status('We need more space for the lab'), 'delivered')

    def test_skills_not_blocked(self):
        # 'kill' (CRITICAL substring) previously auto-blocked any 'skills' message.
        self.assertEqual(self._status('I want to improve my skills'), 'delivered')

    def test_analysis_not_blocked(self):
        self.assertEqual(self._status('Our stress analysis is complete'), 'delivered')

    # --- genuine terms still caught (safeguarding preserved) ---
    def test_standalone_tit_flagged(self):
        self.assertEqual(self._status('tit'), 'flagged')

    def test_standalone_kill_blocked(self):
        self.assertEqual(self._status('I will kill you'), 'blocked')

    def test_obfuscated_term_still_flagged(self):
        # '5h1t' stays SUBSTRING, so it is still caught inside text.
        self.assertEqual(self._status('this is 5h1t honestly'), 'flagged')
