# Moderation Terms

## What is this?

This directory contains two moderation rule files that the platform screens for
in every message sent between users.

### `moderation_terms.txt` — Text terms

A plain-text list (one term per line) covering:

- Literal profanity and slurs
- Obfuscated variants (e.g. `sh1t`, `a$$hole`, `f.u.c.k`)
- Multi-word safeguarding phrases (e.g. `how to kill`, `how to murder`)
- Drug and alcohol references
- Contact-detail leak patterns (email addresses, URLs, Microsoft Teams handles)

### `emoji_moderation_terms.csv` — Emoji rules

A CSV file with columns: `emojis`, `meaning`, `context`, `severity`, `notes`.

Each row describes one or more emoji that may indicate sexual, drug-related,
safeguarding, or violent content when sent between users.

## How to import text terms

```bash
docker exec spt-mentoring-backend-1 python manage.py import_moderation_terms
```

The command is **idempotent** — safe to run multiple times.

### Text-term flags

| Flag | Effect |
|---|---|
| `--dry-run` | Print what would change without writing to the database |
| `--deactivate-missing` | Deactivate rows absent from the current file |
| `--file <path>` | Use a different input file |
| `--source <tag>` | Override the source tag (default: `bulk_import_v1`) |

## How to import emoji terms

```bash
docker exec spt-mentoring-backend-1 python manage.py import_emoji_terms
```

The importer reads `data/moderation/emoji_moderation_terms.csv` and upserts
rules into the `ModerationTerm` table using the `emoji_bulk_v1` source tag.

### Emoji CSV column meanings

| Column | Description |
|---|---|
| `emojis` | One or more emoji forming the rule pattern (no separator) |
| `meaning` | Human-readable label for what the pattern signals |
| `context` | Broad category: Sexting / Drug selling/buying online / etc. |
| `severity` | LOW / MEDIUM / HIGH / CRITICAL |
| `notes` | Extra context, false-positive notes, escalation conditions |

### OR set vs Combination — the parsing rule

The `emojis` field is parsed as a **Unicode grapheme cluster sequence**.
A row is classified based on how many grapheme clusters are in that field and
whether the `meaning` field contains a forward slash (`/`):

| Condition | Classification | Behaviour |
|---|---|---|
| 1 grapheme cluster | `EMOJI_SINGLE` | Fires if that emoji appears anywhere in the message |
| 2+ clusters, **meaning contains `/`** | `EMOJI_OR_SET` | Any one emoji triggers the rule |
| 2+ clusters, **meaning has no `/`** | `EMOJI_COMBO` | ALL emojis must be present within the proximity window |

**Example:**
- `💵💯` with meaning `'Go for it' / consent` → OR set (either emoji triggers)
- `🍆🍑` with meaning `Anal sex` → combination (both must co-occur)

### Proximity window for COMBO rules

`EMOJI_COMBO` rules fire only when all emojis appear within **N positions** of
each other in the emoji-only sequence extracted from the message (non-emoji
characters are ignored during emoji matching).

The default window is **N = 10**.  To change it, set the Django setting:

```python
EMOJI_COMBO_PROXIMITY = 10  # in settings.py
```

A larger value catches spread-out combos; a smaller value reduces false
positives in long messages.

### Ambiguous COMBO rows

Some rows contain emojis that look like independent code words for the same
substance or act (e.g. the cocaine row `❄️🥛⚪🎱`).  The parsing rule
classifies these as COMBO (since `meaning` has no `/`), but they may work
better as OR sets.

The importer **flags these rows as AMBIGUOUS** in its summary output and in the
Django admin changelist.  A safeguarding reviewer should open the admin, filter
by `EMOJI_COMBO` and `source = emoji_bulk_v1`, and change any ambiguous rows to
`EMOJI_OR_SET` if appropriate.

### Emoji-term flags

| Flag | Effect |
|---|---|
| `--dry-run` | Print what would change without writing to the database |
| `--deactivate-missing` | Deactivate `emoji_bulk_v1` rows absent from the current file |
| `--file <path>` | Use a different input file |
| `--source <tag>` | Override the source tag (default: `emoji_bulk_v1`) |

## Risk scoring model

Rather than a simple block/allow decision, emoji rules feed into a numeric risk
score.  This prevents high false-positive rates from common single emojis
(e.g. 🔥 🍑 🍆 are ubiquitous in everyday conversation).

### Score contribution per rule type

| Rule type | Severity | Score added |
|---|---|---|
| Text rule | CRITICAL | 100 |
| Text rule | HIGH | 80 |
| Text rule | MEDIUM | 50 |
| Text rule | LOW | 20 |
| `EMOJI_COMBO` | HIGH | 80 |
| `EMOJI_COMBO` | MEDIUM | 50 |
| `EMOJI_OR_SET` | HIGH | 60 |
| `EMOJI_OR_SET` | MEDIUM | 40 |
| `EMOJI_SINGLE` | HIGH | 30 |
| `EMOJI_SINGLE` | MEDIUM | 15 |
| `EMOJI_SINGLE` | LOW | 5 |
| Cross-signal boost | any (text + emoji both fire) | +20 |

### Score → action mapping

| Score range | Action |
|---|---|
| ≥ 80 | Message **blocked**, sender notified, admin alerted |
| 50 – 79 | Message **held for review** (sender told it's pending), admin sees in queue |
| 20 – 49 | Message **delivered**, logged for admin review queue (no sender notification) |
| < 20 | Message **delivered**, audit log only |

**Critical design principle:** `EMOJI_SINGLE` alone can never auto-block a
message.  The maximum score from a single isolated emoji rule is 30 (HIGH
severity), which falls in the 20–49 "deliver + review queue" band.  Auto-block
requires either a combo rule, an OR-set rule, or a text rule.

### Cross-signal example

A message like `🔥 got some weed delivery`:
- `weed` text rule: LOW → +20
- `🔥` emoji SINGLE: LOW → +5
- Cross-signal boost (both fired): +20
- **Total: 45** → delivered but added to admin review queue

## Safety rule — admin-added terms are never touched

Admins can add custom moderation terms directly through the Django admin panel.
Set the `source` field to `admin` (or leave the default).

**The importer will never update, deactivate, or delete rows whose `source`
differs from its own source tag (`bulk_import_v1` / `emoji_bulk_v1`).**

## Safeguarding review requirement

> ⚠️ **This emoji list must be reviewed by the named safeguarding lead before
> the platform goes live, and re-reviewed every quarter.**

Review checklist:
1. Export the current active emoji ruleset from the admin changelist
   (select all → "Export selected emoji rules to CSV").
2. Review each COMBO row — decide if it should be EMOJI_OR_SET instead.
3. Check severity ratings; escalate or de-escalate as appropriate.
4. Update the CSV file with any corrections.
5. Re-import with `--source emoji_bulk_v2` after changes to keep audit trail.
6. Document the review date and reviewer name in the platform incident log.

> ⚠️ Do NOT change the CSV column schema without updating this README and
> bumping the `--source` to `emoji_bulk_v2` (or higher).  The source tag is
> the audit trail.
