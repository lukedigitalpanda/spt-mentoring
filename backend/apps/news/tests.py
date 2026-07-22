"""Tests for the news app.

Task 24: rich text bodies for News articles are stored as sanitised HTML
(nh3 whitelist) rather than plain text. These tests pin the sanitiser's
contract - what survives, what is stripped - independent of the admin
form that calls it.
"""
from django.test import TestCase

from .sanitiser import is_rich_text, sanitise_rich_text


class SanitiseRichTextTests(TestCase):
    def test_script_tag_is_stripped(self):
        result = sanitise_rich_text('<p>Hello</p><script>alert(1)</script>')
        self.assertNotIn('<script', result)
        self.assertNotIn('alert(1)', result)

    def test_onclick_attribute_is_stripped(self):
        result = sanitise_rich_text('<p onclick="alert(1)">Hello</p>')
        self.assertNotIn('onclick', result)
        self.assertIn('Hello', result)

    def test_whitelisted_formatting_tags_are_kept(self):
        html = '<p><b>bold</b> <i>italic</i></p>'
        result = sanitise_rich_text(html)
        self.assertIn('<b>bold</b>', result)
        self.assertIn('<i>italic</i>', result)

    def test_lists_are_kept(self):
        html = '<ul><li>one</li></ul><ol><li>two</li></ol>'
        result = sanitise_rich_text(html)
        self.assertIn('<ul>', result)
        self.assertIn('<li>one</li>', result)
        self.assertIn('<ol>', result)
        self.assertIn('<li>two</li>', result)

    def test_https_link_is_kept_with_safe_rel(self):
        result = sanitise_rich_text('<a href="https://example.com">link</a>')
        self.assertIn('href="https://example.com"', result)
        self.assertIn('rel="noopener noreferrer"', result)

    def test_span_with_color_style_is_kept(self):
        result = sanitise_rich_text('<span style="color: #ff0000">red text</span>')
        self.assertIn('color:#ff0000', result.replace(' ', '').replace(';', ''))
        self.assertIn('red text', result)

    def test_javascript_href_is_removed(self):
        result = sanitise_rich_text('<a href="javascript:alert(1)">click</a>')
        self.assertNotIn('javascript:', result)

    def test_style_values_other_than_color_are_dropped(self):
        # Only a bare `color: ...` declaration is preserved; a style value
        # combining color with any other property is not partially trimmed
        # down to the color - it is dropped in full (see the "no color"
        # case below), same as any other disallowed style.
        result = sanitise_rich_text('<span style="position: fixed">x</span>')
        self.assertNotIn('position', result)
        self.assertNotIn('style', result)
        self.assertIn('x', result)

    def test_style_with_no_color_is_dropped_entirely(self):
        result = sanitise_rich_text('<span style="font-size: 40px">x</span>')
        self.assertNotIn('style', result)
        self.assertIn('x', result)

    def test_plain_text_passes_through_unchanged(self):
        result = sanitise_rich_text('Just some plain text, no markup at all.')
        self.assertEqual(result, 'Just some plain text, no markup at all.')

    def test_empty_body_returns_falsy_unchanged(self):
        self.assertEqual(sanitise_rich_text(''), '')
        self.assertIsNone(sanitise_rich_text(None))

    def test_underline_tag_survives(self):
        # TinyMCE's toolbar is configured (settings.TINYMCE_DEFAULT_CONFIG,
        # 'formats': {'underline': {'inline': 'u'}}) to emit a bare <u> tag
        # for the underline button instead of its default
        # <span style="text-decoration: underline">, which our style
        # whitelist (color only) would otherwise strip. That config choice
        # isn't headlessly testable, but this pins that the sanitiser itself
        # keeps <u> whenever it's actually produced.
        result = sanitise_rich_text('<u>underlined</u>')
        self.assertIn('<u>underlined</u>', result)


class IsRichTextTests(TestCase):
    """is_rich_text() is the single canonical "does this body contain
    markup" test shared by model save(), admin clean_body() and the
    mass-message email task - pinning its behaviour here covers all of
    them at once."""

    def test_plain_text_is_not_rich(self):
        self.assertFalse(is_rich_text('Just plain text, no markup at all.'))

    def test_ampersand_alone_is_not_rich(self):
        self.assertFalse(is_rich_text('Q&A session'))

    def test_bare_less_than_alone_is_not_rich(self):
        self.assertFalse(is_rich_text('<18 years old'))

    def test_empty_and_none_are_not_rich(self):
        self.assertFalse(is_rich_text(''))
        self.assertFalse(is_rich_text(None))

    def test_real_tag_is_rich(self):
        self.assertTrue(is_rich_text('<p>Hello</p>'))
        self.assertTrue(is_rich_text('plain lead-in <script>alert(1)</script>'))

    def test_prose_that_looks_like_a_tag_is_treated_as_rich(self):
        # Accepted edge case (safety-first, deliberate): text that merely
        # *resembles* a tag - "<a and b>" reads as an <a ...> opening tag
        # to the regex - is classified as rich and will be run through the
        # sanitiser. This is the safety-first direction: false positives
        # here cost a little unnecessary sanitisation of odd prose; false
        # negatives would let real markup slip through unsanitised.
        self.assertTrue(is_rich_text('see <a and b> options'))


class NewsItemBodySanitisedOnSaveTests(TestCase):
    """Task 24 hardening: NewsItemViewSet (REST API) writes body without
    going through the admin form's clean_body(), so the gate must also live
    on the model - sanitise_rich_text() must run on every save(), not just
    on the admin form path."""

    def test_script_in_body_is_stripped_when_created_via_the_orm(self):
        from .models import NewsItem
        item = NewsItem.objects.create(
            title='Test article',
            slug='test-article-orm-sanitise',
            body='<p>Hello</p><script>alert(1)</script>',
        )
        item.refresh_from_db()
        self.assertNotIn('<script', item.body)
        self.assertNotIn('alert(1)', item.body)
        self.assertIn('Hello', item.body)

    def test_plain_text_body_is_unaffected_by_save(self):
        from .models import NewsItem
        item = NewsItem.objects.create(
            title='Plain article',
            slug='test-article-orm-plain',
            body='Just plain text.',
        )
        item.refresh_from_db()
        self.assertEqual(item.body, 'Just plain text.')

    def test_empty_body_saves_safely(self):
        from .models import NewsItem
        item = NewsItem.objects.create(
            title='Empty body article',
            slug='test-article-orm-empty',
            body='',
        )
        item.refresh_from_db()
        self.assertEqual(item.body, '')

    def test_ampersand_in_plain_body_is_stored_byte_identical(self):
        # Regression: nh3 HTML-escapes bare '&' even in tag-free input, so
        # running every body through sanitise_rich_text() unconditionally
        # turned "Q&A session" into "Q&amp;A session" on save. Gating on
        # is_rich_text() keeps genuinely plain text untouched.
        from .models import NewsItem
        item = NewsItem.objects.create(
            title='Q&A article',
            slug='test-article-orm-ampersand',
            body='Join our Q&A session this Friday.',
        )
        item.refresh_from_db()
        self.assertEqual(item.body, 'Join our Q&A session this Friday.')

    def test_bare_less_than_in_plain_body_is_stored_byte_identical(self):
        from .models import NewsItem
        item = NewsItem.objects.create(
            title='Age restriction article',
            slug='test-article-orm-lessthan',
            body='<18 years old? Ask a parent to help you sign up.',
        )
        item.refresh_from_db()
        self.assertEqual(item.body, '<18 years old? Ask a parent to help you sign up.')


class NewsItemAdminFormCleanBodyTests(TestCase):
    """Task 24 hardening: the admin form's clean_body() must apply the same
    is_rich_text() gate as the model save() - plain text must survive the
    form's cleaning step byte-identical, not just the eventual save()."""

    def _clean_body(self, body):
        # NewsItemAdminForm requires other model fields too, but we only
        # care about what clean_body() does to `body` here - other field
        # errors don't stop is_valid() from running _clean_fields(), which
        # is what populates cleaned_data['body'] via clean_body().
        from .admin import NewsItemAdminForm
        form = NewsItemAdminForm(data={'body': body})
        form.is_valid()
        return form.cleaned_data['body']

    def test_ampersand_in_plain_body_unchanged_through_form_clean(self):
        self.assertEqual(self._clean_body('Q&A session'), 'Q&A session')

    def test_bare_less_than_in_plain_body_unchanged_through_form_clean(self):
        self.assertEqual(self._clean_body('<18 years old'), '<18 years old')

    def test_script_body_is_still_stripped_through_form_clean(self):
        result = self._clean_body('<p>Hello</p><script>alert(1)</script>')
        self.assertNotIn('<script', result)
        self.assertNotIn('alert(1)', result)
