# Early-Release Testing Round - Fix Summary

**Date:** 2026-07-22
**Branch:** `feature/notifications-sprint`
**Testers:** 19 mentors and scholars (broad early-release round)
**Scope:** All P1, P2 and P3 items, plus the News/Mass-message rich-text feature.

Every item below was implemented test-first where it touches messaging, moderation, notifications or privacy, reviewed task-by-task (spec compliance and code quality), and fixed through a review loop before being marked complete. Full backend suite: 330 tests passing. Frontend: `tsc` clean, production build clean. No missing migrations; Django system check clean.

British English throughout, no em dashes, no smart quotes, no emoji, as required.

---

## Definition-of-done note on verification

"Verified" below means: automated tests pass (backend) and the code compiles and builds (frontend), plus targeted adversarial review. Items marked **needs device check** still want a final look on a real phone, and the rich-text editor wants a manual admin smoke test (see Deployment). These could not be exercised headlessly.

---

## PRIORITY 1

### P1-1 Composer sends on Enter, no line breaks
**Root cause:** the chat composer was a single-line `<input>` (`MessagesPage.tsx`) with an inline Enter-sends handler; an `<input>` cannot hold newlines at all.
**Fix:** replaced with an auto-growing `<textarea>` (grows to ~160px then scrolls). Desktop: `Enter` sends, `Shift+Enter` inserts a newline. Touch devices (detected via `pointer: coarse`): `Enter` inserts a newline and sending is via the Send button only. The Send button remains always available.
**Files:** `frontend/src/pages/MessagesPage.tsx`.
**Migration/config:** none. **Verified:** build; **needs device check** for the touch-keyboard behaviour.
**Commits:** a56d3a2, 75a2062.

### P1-2 Whitespace and formatting stripped
**Root cause:** the backend already preserved internal whitespace (only a whole-body `.strip()` in `consumers.py`); the collapse was purely the browser rendering `{msg.body}` with no `white-space` rule.
**Fix:** message bubbles now render with `whitespace-pre-wrap break-words`, so newlines, runs of spaces and pasted structure survive input, storage, WebSocket delivery and history load. A regression test asserts internal whitespace and newlines survive the API round-trip.
**Files:** `frontend/src/pages/MessagesPage.tsx`, `backend/apps/messaging/tests.py`.
**Migration/config:** none. **Verified:** test + build.
**Commits:** a56d3a2, 0ad362c.

### P1-3 Mobile chat close to unusable; mobile experience poor
**Root cause:** the chat used a fixed `h-[calc(100vh-14rem)]` height with a fixed `w-72` sidebar and no responsive breakpoints; the draft was one page-level state value that a rotation-triggered reload wiped.
**Fix:**
- Mobile-first single-pane layout: below `md` the conversation list and the open thread are separate full-width panes with a back button; the container uses `100dvh` (tracks the mobile keyboard/chrome) and only `100vh` at `md+`. The message list scrolls, the composer stays docked, no outer-page or horizontal scroll.
- The draft is now held per conversation in `sessionStorage`, so it survives an orientation-change reload and switching threads.
- App-wide overflow sweep at 360/390/414px: forum post bodies wrap (also resolves **P3-6**), the notification bell is reachable in the mobile header, and long free-text fields across Home, Sessions, Goals, Find a Mentor were guarded against horizontal overflow.
**Files:** `frontend/src/pages/MessagesPage.tsx`, `ForumsPage.tsx`, `HomePage.tsx`, `SessionsPage.tsx`, `GoalsPage.tsx`, `MentorDiscoveryPage.tsx`, `components/layout/Layout.tsx`.
**Migration/config:** none. **Verified:** build; **needs device check** at the target widths.
**Commits:** c0674f7, a3b7275.

### Extra: full-app mobile audit (owner-requested mid-round)
On the owner's steer that the responsive mobile web view must be flawless, a dedicated audit pass covered the pages not touched above: fixed the Admin page's `w-64` search input overflow (Users/Cohorts/Resources tab headers), raised auth-page inputs to 16px to stop iOS zoom-on-focus, enlarged survey rating touch targets, and added body wrapping on the News article page. Two structural items were logged as recommendations rather than actioned (auth pages to `min-h-dvh`; the admin cohort-members panel to reflow rather than horizontally scroll).
**Files:** `AdminPage.tsx`, `LoginPage.tsx`, `ForgotPasswordPage.tsx`, `ResetPasswordPage.tsx`, `SurveysPage.tsx`, `NewsArticlePage.tsx`, `MessagesPage.tsx`. **Verified:** build; **needs device check**. **Commit:** ec0d8d6.

---

## PRIORITY 2

### P2-1 Moderation gives no reason and appears to swallow messages
**Root cause (four compounding):** (1) non-staff, including the sender, only ever saw `status=DELIVERED`, so a held message vanished from the sender's own thread; (2) `ModerationService.approve()` changed status but sent the sender no notification and did no live delivery, despite the response copy promising it; (3) the admin `mark_delivered` bulk action used `queryset.update()`, bypassing signals entirely; (4) the reason existed in the moderation result but was never surfaced.
**Fix:**
- Senders now see their own `flagged`/`blocked` messages in their thread (other participants still never do; previews/unread stay DELIVERED-only, so no held content leaks).
- Held/blocked responses carry a safe, category-level reason ("it contains a web link", "it appears to contain contact details", or a generic not-permitted phrase) - never the term list. The frontend composes full sentences from it and shows a "Pending review" or "Not delivered" badge on the sender's own bubble.
- `approve()` now notifies the sender ("Your message has been approved") and broadcasts the released message live over WebSocket; the recipient notification continues to fire via the existing signal, exactly once.
- `mark_delivered` is filtered to `FLAGGED` only and routed through `approve()`, so it can no longer silently un-block a rejected message or duplicate notifications.
- Link policy confirmed: web links are already held for review (never hard-blocked); this work makes that transparent to the sender. See Decisions.
**Files:** `backend/apps/messaging/views.py`, `consumers.py`, `admin.py`, `backend/apps/moderation/service.py`, `frontend/src/pages/MessagesPage.tsx`, `frontend/src/types/index.ts`, tests in messaging + moderation.
**Migration/config:** none. **Verified:** tests (incl. recipient-privacy and release-path tests) + build.
**Commits:** beded2d, 9a60e10, 357a0d5, f4fe86a.

### P2-2 Cannot send ZIP; cannot attach files in Forums
**Root cause:** the attachment validator had no ZIP type; forum posts had a model attachment field and serializer slot but no upload UI and no validation wired.
**Fix:** ZIP added to a single shared validator now used by both chat and forum attachments (consistent types and 20MB limit). Forum reply form gained an upload control with the filename shown before submit and the attachment rendered as a download link; chat surfaces upload rejections instead of failing silently and delivers attachments live (the broadcast now carries the file URL). New-thread first-post attachments and a sidebar paperclip indicator were intentionally left out (noted below).
**Files:** `backend/apps/users/validators.py`, `backend/apps/forums/serializers.py`, `backend/apps/messaging/views.py`, `backend/apps/moderation/service.py`, `frontend/src/pages/ForumsPage.tsx`, `MessagesPage.tsx`, tests in users + forums.
**Migration/config:** none. **Verified:** tests + build.
**Commits:** 2406193, 37e66af.
**Known limitation:** the content type is taken from the browser, not magic-byte sniffed (pre-existing, applies to all types) - backlog: add `python-magic`.

### P2-3 Email notifications not firing reliably
**Root cause:** match/assignment sent no email at all (in-app only, despite the onboarding promise); forum replies notified nobody; the no-contact reminder named no one and had no link.
**Fix:**
- Match/assignment now emails both parties, naming the counterpart and their role and linking straight to `/messages` - and the underlying reinstatement branch was tightened so a benign admin edit of an active match no longer re-fires the notification/email.
- Forum replies now notify every prior thread participant (with debounced email), de-duplicated against the existing scholar-post-to-mentor notification.
- The no-contact reminder now names the mentoring partner and their role and links to the platform; the sponsor reminder gained the platform link.
- Notification preferences are honoured on every send path (verified during the audit).
**Files:** `backend/apps/messaging/tasks.py`, `backend/apps/users/signals.py`, `backend/apps/forums/services.py` + `signals.py` + `models.py` (+ migration), `backend/apps/notifications/emails.py` + `email_catalogue.py`, tests.
**Migration/config:** forums migration (`participants_notified`); run `sync_email_catalogue` at deploy.
**Verified:** tests + catalogue sync.
**Commits:** 8830717, 1258197, 67cc4c0, e2f6f3d.

### P2-4 Cannot edit a sent message, especially one that failed moderation
**Root cause:** no edit feature existed, and worse, both message and post viewsets left PATCH routable with no ownership check and no re-moderation.
**Fix:** senders can edit their own messages (own held ones any time; delivered ones within 15 minutes) and authors can edit their own posts; every edit resets status and re-runs moderation, keeping the held-content-editable loop that pairs with P2-1. Edits show an "(edited)" marker; the history/audit trail is retained. The unmoderated PATCH holes are closed (sender/author-only, PUT/DELETE removed or admin-gated). Held/hidden forum posts are now visible to their author so they can be fixed. A screening-pipeline exception now holds the post for review instead of 500-ing it into an invisible state.
**Files:** `backend/apps/messaging/models.py` (+ migration), `serializers.py`, `views.py`, `signals.py`, `consumers.py`; `backend/apps/forums/views.py`, `serializers.py`, `models.py` (+ migration); `frontend/src/pages/MessagesPage.tsx`, `ForumsPage.tsx`, `types/index.ts`; tests.
**Migration/config:** messaging (`edited_at`) and forums (`edited_at`) migrations.
**Verified:** tests (full permission and signal-suppression matrices, adversarial probes) + build.
**Commits:** 7cab9ff, 27dac44, 991c6e0, 181e51c, 20167c2.

---

## PRIORITY 3

| Item | Fix | Commit |
|---|---|---|
| P3-1 Chat shows time not date | Day separators (Today/Yesterday/full date) plus full date-time on hover | dac62b8 |
| P3-2 Mentor descriptions cut off | Read more / Show less toggle on Find a Mentor bios | 23bd4ca |
| P3-3 Session booking unintuitive | Scholar can withdraw a pending request (a156c50 area); mentors can propose a session at a specific date/time for scholar confirmation; overlapping unbooked availability windows merge on creation; the join button stays visible on confirmed sessions with an availability hint | 8ae3f99, 4a7344f, 9b267cc, a156c50 |
| P3-4 Goals sorting and date labels | Sort by due date (soonest/latest) or newest; date inputs labelled "Target completion date" / "Milestone due date" | dd4023a |
| P3-5 Shared documents hard to find | "Shared documents" link in the chat header and a dashboard quick link, anchored to the profile section | 39e56d0 |
| P3-6 Forum posts cut off | Fixed with the P1-3 forum overflow work | a3b7275 |
| P3-7 Cannot find change-password | It already existed; made discoverable via a "Change password" item in both desktop and mobile menus and a clearer Security heading | 39e56d0 |
| P3-8 Add Astronautics | Added to all four discipline lists; also fixed a drift where Find a Mentor was missing "Structural" | fe16214 |

P3-3 also hardened two pre-existing session bugs found during review: `confirm` now rejects non-pending sessions, and mentor-proposed sessions require the other party to confirm.

---

## Feature: rich text for News and Mass messages

Admins can now format News articles and Mass messages (bold, italic, underline, colour, bullet/numbered lists, links) via a TinyMCE editor in the Django admin. Content is sanitised to a strict allowlist with `nh3` at the **model level** (`save()`), so every write path - admin form and DRF API - is covered; a tag-free body is stored byte-identical (so "Q&A" and "<18" are never mangled). Mass-message emails send as HTML with a plain-text fallback, gated on the body actually containing markup.

The frontend renders this via a single `RichText` component - the app's only `dangerouslySetInnerHTML` - which trusts backend-sanitised HTML only and is used solely for News bodies and the one system-authored announcement message. That gate is a server-set, read-only `Message.is_broadcast` field (not a positional guess), so a user's or an admin's reply in an announcement thread can never be rendered as raw HTML. The sanitiser passed a full adversarial probe battery (script/svg/onerror, javascript:/data: URLs with entity and whitespace tricks, CSS `url()`/`expression()`, homoglyph schemes, malformed nesting).
**Files:** `backend/requirements.txt`, `config/settings.py`, `backend/apps/news/sanitiser.py` + `models.py` + `admin.py`, `backend/apps/messaging/models.py` (+ migration) + `admin.py` + `tasks.py` + `serializers.py`, `frontend/src/components/ui/RichText.tsx`, `index.css`, `NewsArticlePage.tsx`, `MessagesPage.tsx`, tests.
**Migration/config:** messaging `is_broadcast` migration; **image rebuild required** for `django-tinymce==5.0.0` and `nh3==0.3.6`; run `collectstatic`.
**Verified:** tests + build + adversarial sanitiser review. **Needs manual admin smoke test** of the editor widget.
**Commits:** 4e8ae11, 62b7137, bcd8504, 15a3391, f3a696a, 4c688cb, ff99c8a.

---

## Security hotfix (found during P3-3 review)

The `MentoringMatch` API (`/api/users/matches/`) was readable by any authenticated user - exposing every mentor-scholar pairing, including free-text notes - and its `partial_update` was not admin-gated, so any authenticated user could PATCH any match (flip `is_active`, rewrite notes, reassign people). Now scoped: non-staff see only their own matches; all writes are admin-only. No frontend depended on the open behaviour (grep-confirmed zero call sites). **This exposure existed in production and is worth noting to the owner.**
**Commit:** 0df6f2e.

---

## Decisions needed (raised, not built)

1. **Rich text inside chat/forum messages** - multiple mentors want it; larger than the admin editor and interacts with moderation of formatted content. The sanitiser and `RichText` component built here are reusable if greenlit.
2. **Read receipts** (Tom Knight) - confirm whether to add.
3. **Christopher Baillie cannot message his mentor** - investigated in production: his account is an active scholar with **zero `MentoringMatch` rows** (only a support conversation with Arkwright). Not a code defect - he was never matched on the platform. Remedy: the SPT team creates the match in admin, which now auto-emails both parties.
4. **Mentornet data migration** - scope/feasibility decision.
5. **Link policy** - links between matched pairs are held for review (never hard-blocked) and this is now transparent to the sender; whether to whitelist Teams/Zoom domains for matched pairs is a product call.
6. **Mentoring contract / partnership description** - content decision.
7. **Visual polish pass** - subjective, deferred.

Two smaller items also worth a decision: new-thread first-post attachments in Forums (replies are covered), and consolidating messaging + sessions + shared documents into a single mentor hub (P3-5 made the documents reachable in the meantime).

---

## Deployment checklist

1. Rebuild the backend image (`requirements.txt` adds `django-tinymce==5.0.0`, `nh3==0.3.6`).
2. `python manage.py migrate` (messaging: `edited_at`, `is_broadcast`; forums: `participants_notified`, `edited_at`).
3. `python manage.py sync_email_catalogue` and `python manage.py collectstatic --noinput`.
4. Rebuild and redeploy the frontend image.
5. `docker compose up -d` (env/app changes need container recreation, not just a restart).
6. Manual checks that could not be done headlessly: the P1 chat behaviours on a real phone at 360/390/414px, and the TinyMCE editor loading and saving correctly in the jazzmin admin for a News article and a Mass message.
