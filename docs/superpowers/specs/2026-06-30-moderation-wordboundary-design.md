# Moderation: word-boundary matching for plain-letter terms

**Date:** 2026-06-30
**Status:** Approved (design)
**Author:** Claude + Luke

## Problem

Moderators report that legitimate words are being flagged/blocked because short
moderation terms match as *substrings* inside innocent words:

- `af` fires inside **af**ternoon, dr**af**t, st**af**f
- `tit` fires inside **tit**le, compe**tit**ion, ins**tit**ute
- `spac` fires inside **spac**e, **spac**ious

This is systemic, not three bad rows. The `ModerationTerm` table holds **1,145**
active `SUBSTRING` terms; **968 are plain alphabetic** and **177 are obfuscated**
(leet/symbol forms such as `a$$`, `5h1t`, `b1tch`). The worst offenders are in the
**HIGH / auto-block** tier:

- `kill` (substring) auto-blocks any message containing **skill / skills / skilled**
- `anal` auto-blocks **anal**ysis / **anal**yst / c**anal**
- `spic` auto-blocks **spic**y / su**spic**ious / de**spic**able
- `sex` blocks Su**ssex**; `cum` flags do**cum**ent; `dick` flags **Dick**ens

This wastes large amounts of moderator review time and (for the HIGH tier)
silently blocks normal mentoring conversation.

## Goal

Stop in-word false positives while preserving safeguarding coverage. No weakening
of the obfuscation-evasion detection that substring matching exists to provide.

## Approach

**Convert plain-letter terms to whole-word (word-boundary) matching; leave
obfuscated terms as substring.**

- **Plain alphabetic terms** (`^[A-Za-z]+$`) → `match_type` `SUBSTRING` → `EXACT`.
  The engine already compiles `EXACT` as `(?i)\b<term>\b`, so `tit` matches the
  standalone word `tit` but not `title`. Genuine bad compounds (`cockhead`,
  `fuckface`, `dickheads`, `cocks`, …) are **already separate rows**, so nothing
  is lost there.
- **Obfuscated terms** (contain a digit, symbol or space) → **unchanged**
  (`SUBSTRING`). They never occur inside real English words, and substring is
  exactly what catches that evasion.
- Applies to **all severities**, including CRITICAL — the auto-block tier is where
  the most damaging false positives live (`kill`→skills, `anal`→analysis).

### Accepted trade-off

Word-boundary matching will **not** catch elongated or run-together evasion of a
plain-letter term — e.g. `fuckkkk` or `idiotcock` — that bare substring currently
would. All listed plurals/compounds and all obfuscated forms still match. Signed
off as acceptable given the threat model (mentor ↔ scholar, human review of
flagged items).

### Data facts (verified 2026-06-30)

- 968 plain-letter `SUBSTRING` terms to convert.
- 0 collisions: no term already exists as an `EXACT` row, so the bulk update
  cannot violate `unique_together('term', 'match_type')`.
- 0 case-insensitive duplicates among the converted set.

## Mechanism

A Django management command in `apps/moderation/management/commands/`,
`convert_plain_substring_terms.py`:

1. Select `ModerationTerm` rows where `match_type='SUBSTRING'` and
   `term` matches `^[A-Za-z]+$` (Python regex; DB filter narrows, Python confirms).
2. `--dry-run` prints the count and a sample without writing.
3. Without `--dry-run`: bulk-update `match_type` → `EXACT`. Guard each row against
   an existing `EXACT` twin (delete the substring row instead of updating) so the
   command stays safe even though current data has no collisions.
4. Call `ModerationService.invalidate_cache()` at the end so the running process
   rebuilds its compiled pattern cache.

Chosen over an engine change (which would alter matching semantics globally and
implicitly) and over a data migration (a hand-run command with `--dry-run` is
safer and more controllable on the live mounted deployment, and matches the
existing `apps/moderation/management/commands` import-command pattern).

Deployment: run `--dry-run`, then for real, then `docker compose restart backend`
(daphne, no hot-reload).

## Testing (TDD)

Behavioural tests against `ModerationService.screen_text` with seeded
`ModerationTerm` rows (fresh test DB — not prod data):

**Now pass cleanly (regression — previously flagged/blocked):**
- "Let's meet this afternoon" → delivered
- "What is the title of your project?" → delivered
- "We need more space for the lab" → delivered
- "I want to improve my skills" → delivered (was auto-blocked by `kill`)
- "Our stress analysis is complete" → delivered (was auto-blocked by `anal`)

**Still caught (safeguarding preserved):**
- A message of just `tit` (standalone) → flagged
- `kill` used as a standalone word → blocked
- An obfuscated term such as `5h1t` → still flagged via substring

**Command unit test:**
- Seed a plain `SUBSTRING` term + an obfuscated `SUBSTRING` term; run the command;
  assert the plain one became `EXACT` and the obfuscated one is unchanged.

## Tasks

1. Write failing behavioural tests in `apps/moderation/tests/`.
2. Write the management command; make tests green.
3. Run `--dry-run` on production, eyeball the count (expect ~968), then run for real.
4. `invalidate_cache()` + restart backend; spot-check the reported phrases live.
5. (Follow-up, optional) default future bulk imports to a smarter match_type so
   re-imports don't reintroduce the problem.

## Out of scope

- Re-categorising or re-scoring terms.
- Changing the importer (noted as optional follow-up).
- Legacy `BlockedTerm` / `FlaggedTerm` tables — they already match on word
  boundaries (`_contains_term`) and are not part of this issue.
