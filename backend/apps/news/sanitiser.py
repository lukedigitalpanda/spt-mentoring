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
    """
    if not html:
        return html
    return nh3.clean(
        html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS,
        url_schemes={'http', 'https', 'mailto'},
        link_rel='noopener noreferrer', attribute_filter=_attr_filter,
    )
