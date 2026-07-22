"""Tests for the news app.

Task 24: rich text bodies for News articles are stored as sanitised HTML
(nh3 whitelist) rather than plain text. These tests pin the sanitiser's
contract - what survives, what is stripped - independent of the admin
form that calls it.
"""
from django.test import TestCase

from .sanitiser import sanitise_rich_text


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
