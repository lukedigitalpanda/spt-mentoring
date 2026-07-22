"""Strict HTML sanitisation for rich text bodies (News articles, Mass messages).

Shared by apps.news and apps.messaging admin forms so both editors produce
the same restricted HTML dialect: basic formatting, lists, links and a
foreground colour on spans - nothing that can execute script or style the
page outside that whitelist.
"""
import re

import nh3

_ALLOWED_TAGS = {'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'a', 'span'}
_ALLOWED_ATTRS = {'a': {'href', 'target'}, 'span': {'style'}}
# NOTE: 'rel' is deliberately excluded from _ALLOWED_ATTRS above. nh3 0.3.6
# manages the "rel" attribute itself whenever link_rel is set (below) and
# raises ValueError if "rel" is also explicitly whitelisted - it is nh3's
# job here, not ours, to stamp every link with the safe rel value.
_COLOR_RE = re.compile(r'^\s*color\s*:\s*(#[0-9a-fA-F]{3,8}|rgb\([\d\s,]+\)|[a-zA-Z]+)\s*;?\s*$')

# Canonical "does this body contain markup at all" test, shared by every
# write path (model save(), admin clean_body(), the mass-message email
# task) so there is exactly ONE definition of "rich" across the backend.
# Task 25's frontend body renderer must mirror this same regex when
# deciding whether to render a body as HTML or display it as plain text -
# the two ends must agree on what counts as "rich" or the two would drift.
#
# Accepted edge case (safety-first, deliberate): prose that merely *looks*
# like a tag - e.g. "see <a and b> options" - matches this regex and will
# be treated as rich (and therefore run through the HTML sanitiser, which
# only touches things outside its whitelist). This is intentional: false
# positives here cost a little unnecessary sanitisation of odd-looking
# prose; false negatives would mean real markup slips through unsanitised.
HTML_TAG_RE = re.compile(r'<([a-z]+)(\s[^>]*)?>', re.IGNORECASE)


def is_rich_text(text):
    """True if `text` contains what looks like an HTML tag.

    Plain text with no tags at all (the overwhelmingly common case for
    both News articles and Mass messages) must never be run through
    sanitise_rich_text(): nh3 HTML-escapes bare `&`/`<`/`>` characters in
    plain text nodes ("Q&A" -> "Q&amp;A", "<18 years old" -> "&lt;18 years
    old"), which is correct when re-embedding text inside HTML but wrong
    when the value is going to be stored/displayed as plain text, since it
    would then show the escaped entities literally.
    """
    return bool(text and HTML_TAG_RE.search(text))


def _attr_filter(tag, attr, value):
    if attr == 'style':
        return value if _COLOR_RE.match(value) else None
    return value


def sanitise_rich_text(html):
    """Clean admin-authored HTML down to a strict whitelist.

    Keeps: p, br, strong/b, em/i, u, ul/ol/li, a (http/https/mailto href
    only, rel forced to noopener noreferrer), span (style limited to a
    bare `color` declaration). Everything else - script tags, event
    handler attributes, javascript: links, other CSS properties - is
    stripped.

    Callers that need to distinguish "no markup, leave byte-identical"
    from "markup present, sanitise" should check is_rich_text() first -
    this function itself sanitises unconditionally (nh3 HTML-escapes bare
    &/</> even in tag-free input, which is correct HTML-embedding
    behaviour but not what a plain-text body wants - see is_rich_text()).
    """
    if not html:
        return html
    return nh3.clean(
        html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS,
        url_schemes={'http', 'https', 'mailto'},
        link_rel='noopener noreferrer', attribute_filter=_attr_filter,
    )
