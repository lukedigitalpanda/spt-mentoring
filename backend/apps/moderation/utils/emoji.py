"""
Grapheme-cluster-aware emoji helpers.

All matching operates on *normalised* emoji — skin-tone modifiers and variation
selectors stripped, ZWJ sequences preserved intact.  This means 🍆🏿 and 🍆 both
normalise to the same canonical form, so a single rule covers all skin-tone
variants.

Dependencies:
  grapheme>=0.6  — Unicode TR29 grapheme-cluster segmentation (pure Python)
  emoji>=2.0     — emoji code-point database and is_emoji() lookup
"""
import grapheme as _grapheme
import emoji as _emoji

# Skin-tone modifiers: U+1F3FB LIGHT through U+1F3FF DARK
_SKIN_TONES: frozenset[int] = frozenset(range(0x1F3FB, 0x1F400))

# Variation selectors: text (U+FE0E) and emoji (U+FE0F)
_VARIATION_SELECTORS: frozenset[int] = frozenset({0xFE0E, 0xFE0F})


def extract_emoji_graphemes(text: str) -> list[str]:
    """Return the list of grapheme clusters in *text* that are (or contain) emoji."""
    return [g for g in _grapheme.graphemes(text) if _emoji.emoji_count(g) > 0]


def normalise_emoji(g: str) -> str:
    """
    Return the canonical form of a single emoji grapheme cluster.

    Strips skin-tone modifiers (U+1F3FB–U+1F3FF) and variation selectors
    (U+FE0E, U+FE0F).  ZWJ (U+200D) and all other codepoints are preserved,
    so compound sequences like 👨‍💻 remain intact and distinct from their parts.
    """
    return ''.join(
        c for c in g
        if ord(c) not in _SKIN_TONES and ord(c) not in _VARIATION_SELECTORS
    )


def normalise_emoji_sequence(text: str) -> str:
    """
    Extract all emoji from *text*, normalise each grapheme cluster, and return
    them concatenated — all non-emoji characters discarded.

    "hello 🍆 world"  →  "🍆"
    "🍆🏿🍑"          →  "🍆🍑"   (skin tone stripped from first)
    """
    return ''.join(normalise_emoji(g) for g in extract_emoji_graphemes(text))
