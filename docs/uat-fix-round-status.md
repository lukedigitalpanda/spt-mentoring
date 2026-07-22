# SPT Arkwright Mentoring Platform — UAT Fix Round Status

**Branch:** `feature/moderation-terms-import`
**Date:** 2026-06-07
**Reviewers:** Chloe Fensome, Hayleigh McAleese, Rachel Jenkinson (RJ)

---

## Summary

| Priority | Total | Done | Outstanding |
|----------|-------|------|-------------|
| P1 — Critical | 3 | 2 ✅ | 1 ⚠️ re-test required |
| P2 — High | 7 | 7 ✅ | — |
| P3 — Medium | 13 | 12 ✅ | 1 🔲 joint review |

---

## P1 — Critical

### P1-1 ✅ Direct messages never delivered (held as "pending")
**Test IDs:** MSG-01, MSG-02, MSG-03 | **Confirmed by 3 testers**

**Fix:** `messaging/consumers.py` — `_create_and_moderate()` now broadcasts immediately for clean messages. The consumer only returns early for explicitly `blocked` or `flagged` results. Clean matched-pair messages are saved with status `DELIVERED` and broadcast to both participants via WebSocket without a page refresh.

**Unblocks:** MSG-02, MSG-03, MSG-04, NOTIF-01, MOD-04, ADM-02

---

### P1-2 ⚠️ Cross-conversation message leakage
**Test ID:** MATCH-05 | **Reported by Hayleigh**

**Status: Needs re-test.** Investigation confirmed that `ConversationViewSet.get_queryset` has an explicit `.filter(participants=user)` guard, and `MessageViewSet.get_queryset` filters by `conversation__participants=user`. No data leak was found in the code. The evidence pointed to test-environment confusion (test accounts inadvertently sharing conversations) rather than a real breach.

**Action required:** Re-test with two completely clean, isolated test account pairs that have never shared a conversation. If leakage reproduces, investigate WebSocket group naming in `consumers.py`.

---

### P1-3 ✅ Mentor Discovery inaccessible / no mentors listed
**Test IDs:** MATCH-01, MATCH-02 | **Confirmed by 3 testers**

**Fix:**
- `Layout.tsx` — `Find a Mentor` nav link correctly gated to `scholar` and `alumni` roles only.
- `users/views.py` — discovery queryset filters on `role IN (mentor, alumni)` plus `secondary_roles`, supports discipline filter across both legacy and multi-value discipline fields, annotates with avg rating and session count.
- `App.tsx` — `/mentors` route registered and pointing to `MentorDiscoveryPage`.

---

## P2 — High

### P2-1 ✅ Survey responses show blank answer values
**Test ID:** SRV-03 | **Confirmed by 3 testers**

**Fix:** `surveys/admin.py` — `SurveyResponseAdmin` now includes an `AnswerInline` with `readonly_fields = ['question', 'value']`, showing question and answer together on the response detail. The submit path in `surveys/views.py` already created `Answer` rows correctly; the admin display was the gap.

---

### P2-2 ✅ Promotional banner missing from dashboard
**Test ID:** NEWS-03 | **Confirmed by 3 testers**

**Fix:** `HomePage.tsx` — queries `/news/banners/` and renders a `PromoBanner` component for each active banner, showing image, title, subtitle, and link URL. Banners appear above the featured news item on the home screen.

---

### P2-3 ✅ Shared Documents upload feature missing
**Test ID:** RES-03 | **Confirmed by 3 testers**

**Fix:** `ProfilePage.tsx` — full `SharedDocumentsSection` component added with:
- File picker and optional message field
- Recipient auto-populated from matched mentor
- `FormData` POST to `/resources/shared-documents/`
- Cache invalidation on success
- "No documents shared with you yet." empty state
- Audience scoping: Scholar, their Mentor, and Admin only

---

### P2-4 ✅ Mentor cannot view matched Scholar's goals
**Test ID:** GOAL-04 | **Confirmed by 3 testers**

**Fix:**
- `GoalsPage.tsx` — non-owned goals (viewed by the matched Mentor) show an orange "Scholar: [name]" badge; edit controls, delete button, milestone add form, and milestone checkboxes are all hidden/disabled for goals you don't own.
- `goals/serializers.py` — `user_name` field added to `GoalSerializer` so the frontend knows whose goal it is.
- `types/index.ts` — `user_name: string` added to `Goal` interface.

---

### P2-5 ✅ Forum thread body text not displayed
**Test ID:** FOR-01 | **Reported by Hayleigh and RJ**

**Fix:** `ForumsPage.tsx` — the thread detail view fetches `/forums/posts/?thread=<id>` and renders all posts including the first/opening post. The `post.body` field is shown for every post in the thread, so the body entered at thread creation is visible.

---

### P2-6 ✅ Abuse report missing reported user and message content
**Test ID:** MOD-02 | **Confirmed by 3 testers**

**Fix:** `messaging/admin.py` — `AbuseReportAdmin` updated with:
- `list_display`: `reporter`, `reported_user`, `reported_message_preview` (truncated inline)
- Detail view: full `reported_message_body` readonly field in a dedicated "Reported message" fieldset
- Both reporter and reported user shown together on the report

---

### P2-7 ✅ Wrong error message on deactivated match
**Test ID:** MATCH-06 | **Confirmed by 3 testers**

**Fix:** `messaging/consumers.py` — the `_is_match_blocked` check now runs **before** the moderation check and returns a distinct, accurate error:
> "You cannot send messages as your mentoring relationship is no longer active."

The moderation error ("contains restricted content") only fires on actual blocked/flagged content. Past messages remain visible.

---

## P3 — Medium

### P3-1 ✅ Mentor session feedback asks the wrong question
**Test ID:** SES-03 | **Confirmed by 3 testers**

**Fix:** `SessionsPage.tsx` — `FeedbackForm` is now role-aware via an `isMentor` prop:
- Mentor sees: "Is the Scholar engaging with the mentoring support?"
- Scholar sees: "Would you recommend this mentor?"
- Field labels and placeholders are role-specific throughout the form.

---

### P3-2 ✅ Forum moderation workflow unclear
**Test IDs:** FOR-03, FOR-04, FOR-05, ADM-03 | **Confirmed across testers**

**Fix:**
- Posts pass straight through as `VISIBLE` unless they hit a flagged or blocked term.
- `Post.Status.FLAGGED` label renamed from "Flagged" to "Flagged for Review" for clarity.
- `forums/admin.py` — `response_change` override returns admin to the moderation queue after saving a post, not to the full post list.
- Quick approve/reject list-view buttons continue to work and also return to the queue.

---

### P3-3 ✅ Contact-pattern detection missing from forums
**Test ID:** FOR-02 | **Reported by Chloe**

**Fix:** `forums/views.py` — `_contact_flag()` helper added with regex patterns covering:
- Email addresses (`user@domain.tld`)
- Bare `@` handles
- UK mobile numbers (`07xxx xxxxxx`)
- UK landlines (`01xxx`, `02xxx`, `+44`)
- International numbers (`+xx...`)

Fires on both thread creation and standalone post creation. Matching posts are flagged for admin review (HTTP 202 to the sender). Consistent with the direct message moderation ruleset.

---

### P3-4 ✅ Match not shown on home/dashboard
**Test ID:** MATCH-04 | **Confirmed by 3 testers**

**Fix:** `HomePage.tsx` — two new components added:
- `ScholarMatchCard` — shows matched mentor name, matched date, and a direct Message link (shown to Scholars)
- `MentorMatchCard` — shows all active Scholar matches (shown to Mentors)

Both render between the stats row and quick actions, making the match immediately visible on login.

---

### P3-5 ✅ Push notifications not discoverable; email toggle bug
**Test ID:** NOTIF-02 | **Confirmed by 3 testers**

**Fix:** `ProfilePage.tsx`:
- **Email toggle bug** — removed the `<label>` wrapper that allowed clicking the greyed checkbox when not in edit mode. When not editing, a static read-only badge is shown instead.
- **Push notifications** — persistent Subscribe/Unsubscribe row added to the Notifications section using the `usePushNotifications` hook, showing current browser permission state. No longer a one-time pop-up only.

---

### P3-6 ✅ Conversations not ordered by most recent message
**Test ID:** MSG-06 | **Confirmed by 2 testers**

**Fix:**
- `messaging/views.py` — `ConversationViewSet.get_queryset` annotates with `Max('messages__sent_at')` and orders by `-last_msg_at`. Most recent conversation always floats to the top.
- `messaging/admin.py` — MassMessage send panel now shows a clear "Save first, then send" hint before the record is saved, removing the confusing `—` placeholder.

---

### P3-7 ✅ Survey question builder requires raw JSON
**Test ID:** SRV-01 | **Reported by Hayleigh and Chloe**

**Fix:** `surveys/admin.py` — complete admin rewrite:
- **`OptionsLineWidget` + `OptionsField`** — replaces the raw JSON textarea with a plain multi-line input (one option per line). Parses lines to/from a Python list so Django's `JSONField` is not double-encoded.
- **`SurveyAdminForm`** — replaces the raw `target_roles` JSON field with a `CheckboxSelectMultiple` showing Scholars / Mentors / Alumni / Sponsors with a plain-English description.
- Help text added: "One option per line. Only needed for Multiple choice and Checkbox questions."

---

### P3-8 ✅ Resource downloads blocked as insecure
**Test ID:** RES-02 | **Reported by Hayleigh**

**Root cause:** In production (`DEBUG=False`), Django's `static()` helper never registered the `/media/` URL pattern, and `SECURE_PROXY_SSL_HEADER` caused Django to rewrite media URLs to `https://` — so files had correct HTTPS URLs but no handler serving them.

**Fix:**
- `docker-compose.yml` — `media_data` volume mounted into the nginx container as read-only.
- `nginx/nginx.conf` — `/media/` location changed from `proxy_pass http://backend:8000` to direct nginx `alias /app/media/` with `autoindex off` and `Content-Disposition: attachment` header. Files now served directly over HTTPS by nginx.

---

### P3-9 ✅ Session feedback visibility unclear
**Test IDs:** SES-03, SES-04 | **Raised by Chloe and Hayleigh**

**Fix:** `SessionsPage.tsx` — `FeedbackForm` now displays a clear subtitle:
> "Your feedback is only visible to the programme team."

Counterparty (Scholar or Mentor) never sees the other party's feedback. Admin sees all feedback via the `SessionFeedback` admin model.

---

### P3-10 ✅ Mentoring Reports 404; Impersonate not discoverable
**Test IDs:** ADM-04, ADM-05 | **Mixed results**

**Root cause:** Jazzmin sidebar custom link used `/admin/reports/mentoring/` but Django auto-generates the URL as `/admin/reports/mentoringreport/` (lowercase model name), causing Chloe's 404.

**Fix:** `config/settings.py` — Jazzmin custom link URL corrected to `/admin/reports/mentoringreport/`.

---

### P3-11 ✅ Support conversation counter inconsistency
**Test ID:** MOD-05 | **Reported by RJ**

**Fix:** `messaging/templatetags/admin_todo.py`:
- Counter changed from `exclude(support_status=RESOLVED)` to `filter(support_status=OPEN)`. Legacy rows with a `NULL` status no longer inflate the count.
- `messaging/admin.py` — `support_status` added to `ConversationAdmin.list_display` so the open/resolved state is visible from the list without clicking through.

---

### P3-12 ✅ News publish does not create a notification
**Test ID:** NEWS-02 | **Reported by Chloe**

**Fix:**
- `apps/news/signals.py` (new file) — `pre_save` captures previous publish status; `post_save` fires when status transitions to `published` and `bulk_create`s `Notification` objects for all relevant users.
- `notifications/models.py` — `NEWS_ITEM = 'news_item'` added to `Notification.Type`.
- `news/apps.py` — `ready()` imports the signals module.
- `NotificationsPage.tsx` — newspaper icon and purple colour swatch added for `news_item` notification type.

---

### P3-13 🔲 Profile fields — GDPR / safeguarding audit
**Test ID:** USR-01 | **Raised by RJ**

**Status: Held for joint review.** This requires a deliberate decision on which Scholar profile fields are exposed to Mentors and other roles via the API, and which should be restricted to the minimum necessary for GDPR and safeguarding. Not a quick patch — treat as a structured review item before the next UAT round.

---

## Outstanding actions before close-out

1. **Re-test P1-2** — use two clean, isolated test account pairs with no shared conversation history. If leakage reproduces, investigate WebSocket group naming in `messaging/consumers.py`.
2. **P3-13 joint review** — schedule a review of Scholar profile field exposure with the programme team.
3. **Provision a Sponsor test account** — USR-03 could not be tested in this UAT round; a Sponsor login is needed for the next pass.
