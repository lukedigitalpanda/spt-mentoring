# Early-Release Testing Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all P1/P2/P3 items from the July 2026 early-release testing round (19 testers) plus the admin rich-text feature, in priority order, without regressing moderation queue, session booking, or goals.

**Architecture:** Django/DRF backend (`backend/apps/*`) with Channels WebSocket chat, Celery/Redis for email, React 18 + Tailwind 3.4 frontend (`frontend/src`). Chat lives entirely in `MessagesPage.tsx`; moderation is `ModerationService` invoked synchronously at message/post creation; email is debounced through `EmailDigest` and audited by `LoggingEmailBackend`/`EmailLog`.

**Tech Stack:** Django 4.x, DRF, Channels, Celery, PostgreSQL, React 18, Vite, Tailwind CSS 3.4 (has `dvh` and `line-clamp` core support), django-tinymce + nh3 (new, rich text feature only).

## Global Constraints

- British English in ALL user-facing copy ("organisation", "programme", "behaviour"). No em dashes, no smart or curly quotes, no emoji in code or copy. Plain hyphens only.
- The working tree has ~136 uncommitted files of PRIOR deployed work. NEVER use `git add -A`, `git add .`, or `git commit -a`. Stage only the exact files each task touches.
- Backend tests run with: `cd /opt/spt-mentoring/backend && python manage.py test apps.<app> -v 1` (if no local venv works, use `docker compose exec backend python manage.py test apps.<app>`). There is NO frontend test framework; frontend verification is `cd frontend && npx tsc --noEmit && npm run build` plus manual/device-emulation checks.
- Any task touching messaging, moderation, notifications, or privacy scoping MUST add or update a backend test proving the behaviour.
- Do not regress: goals with milestones, session booking basics, dashboard/nav, the moderation queue, and the previous UAT round's message-direction fixes (clean matched-pair messages must still deliver + broadcast immediately).
- Existing test that WILL need updating when sender-visibility changes: `apps/messaging/tests.py::MessageHistoryTests::test_history_excludes_blocked_and_flagged_for_non_staff` (non-staff senders will now see their OWN flagged/blocked messages; other participants still must not).
- Frontend chat WS payloads: server sends `{type: 'chat_message', message_id, body, sender_id, sender_name, sent_at}`; new event types added in this plan must be additive so old clients ignore them gracefully.
- `FRONTEND_URL` setting exists (`config/settings.py:240`, default `https://mentoring.smallpeice.online`) - use it for links in emails.

---

## Key root causes (established by investigation, do not re-derive)

| Item | Root cause |
|---|---|
| P1-1 | Composer is a single-line `<input>` at `MessagesPage.tsx:549-555`; inline Enter-sends handler at :552. No textarea, so newlines are impossible. |
| P1-2 | Backend preserves internal whitespace (only whole-body `.strip()` at `consumers.py:34`); collapse is pure HTML rendering - `{msg.body}` at `MessagesPage.tsx:452` has no `whitespace-pre-wrap`. |
| P1-3 | `MessagesPage.tsx:272` `h-[calc(100vh-14rem)]` + fixed `w-72` sidebar (:274), zero responsive breakpoints; draft is one non-persisted `useState` (:46). |
| P2-1 | (a) Non-staff (incl. the sender) only ever see `status=DELIVERED` (`views.py:234-235`) so held messages vanish; (b) `ModerationService.approve()` (service.py:723) sends no sender notification and no channel broadcast despite the 202 copy promising it; (c) admin `mark_delivered` uses `queryset.update()` bypassing signals (admin.py:700); (d) reasons exist in `ModerationResult` (`triggered_rules`, `note`) but are never surfaced. URL fragments already flag-not-block (service.py:396-399). |
| P2-2 | `ALLOWED_ATTACHMENT_TYPES` (`users/validators.py:4-20`) has no ZIP; forum `Post.attachment` field + serializer exist but there is NO frontend upload UI and NO validation wired; REST live-broadcast omits attachment URL so recipients see filename text until refetch. |
| P2-3 | Match/assignment sends NO email (in-app only, `users/signals.py:106-143`); forum replies notify nobody (`FORUM_REPLY` type exists, unused); no-contact reminder (`messaging/tasks.py:11-17`) names nobody and has no link. Chat + scholar-forum-post emails exist and respect `notification_email`. |
| P2-4 | No edit feature; worse, `MessageViewSet` (full ModelViewSet) allows PATCH of any delivered message in your conversations without re-moderation, and `PostViewSet` allows PATCH of ANY visible post by ANY authenticated user with no re-moderation. |
| P3-3 cancel | Backend already allows scholar cancel of pending (`sessions/views.py:113-134`); frontend hides the button for `pending` (`SessionsPage.tsx:247`). |
| P3-7 | Change-password EXISTS (`SecuritySection`, ProfilePage.tsx:584+, `POST /users/me/change-password/`) - discoverability problem only. |
| P3-8 | Disciplines are duplicated constants in 4 places: ProfilePage.tsx:66-69 (11 items), MentorDiscoveryPage.tsx:38-41 (10 items, drifted - missing Structural), users/admin.py (~:33-44 choices, ~:225-228 DISCIPLINES, ~:305-310 specialisms). |

## Decisions needed - raise with owner, DO NOT build

Report these at the end of the round; none are implemented here:

1. Rich text inside chat/forum messages (moderation of formatted content unresolved).
2. Read receipts (Tom Knight).
3. Christopher Baillie cannot message his allocated mentor - Task 23 investigates whether his `MentoringMatch`/conversation rows are missing or inactive in production; likely data, not code.
4. Mentornet data migration.
5. Link policy: links between matched pairs currently HELD for review (never blocked). P2-1 work makes this transparent to the sender; whether to whitelist Teams/Zoom domains for matched pairs is the owner's call.
6. Mentoring contract / partnership description content.
7. Visual polish pass.

---

### Task 1: P1-1 + P1-2 - Multi-line composer, Enter behaviour, whitespace-preserving render

**Files:**
- Modify: `frontend/src/pages/MessagesPage.tsx` (composer :549-555, bubble :434-455, draft state :46, sendMessage :192-221)

**Interfaces:**
- Produces: `draft` state remains a string; `sendMessage()` signature unchanged. Bubble text node gains `whitespace-pre-wrap break-words`. A module-scope `IS_COARSE_POINTER` boolean and a `taRef`/`autoGrow` pattern that Task 3 reuses.

- [ ] **Step 1: Replace the `<input>` with an auto-growing `<textarea>`**

At module scope (top of file, after imports):

```tsx
// Touch-first devices get Enter-inserts-newline; sending is via the button only.
const IS_COARSE_POINTER =
  typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches;
```

Inside the component add:

```tsx
const taRef = useRef<HTMLTextAreaElement>(null);
const autoGrow = () => {
  const el = taRef.current;
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'; // ~6 lines, then internal scroll
};
```

Replace the `<input>` block (lines 549-555) with:

```tsx
<textarea
  ref={taRef}
  rows={1}
  value={draft}
  onChange={e => { setDraft(e.target.value); autoGrow(); }}
  onKeyDown={e => {
    if (e.key === 'Enter' && !e.shiftKey && !IS_COARSE_POINTER) {
      e.preventDefault();
      sendMessage();
    }
  }}
  placeholder="Type a message..."
  className="flex-1 resize-none overflow-y-auto max-h-40 border-2 border-purple-100 rounded-xl px-4 py-2.5 text-sm text-navy-500 bg-[#faf9fd] focus:outline-none focus:border-pink-500 transition-colors placeholder:text-navy-500/30"
/>
```

After a successful send, reset height: in `sendMessage`, immediately after `setDraft('')`, add `if (taRef.current) taRef.current.style.height = 'auto';`. Keep the existing Send button; it must remain the always-available send path.

- [ ] **Step 2: Preserve whitespace in the bubble and trim only the whole message**

Bubble body (line 452): change `{msg.body}` to a wrapper with pre-wrap:

```tsx
<p className="whitespace-pre-wrap break-words">{msg.body}</p>
```

Also add `break-words` + `min-w-0` to the bubble div (:434) so long URLs/code wrap. `sendMessage` already sends `draft.trim()` - whole-message trim is allowed by spec; confirm nothing else touches internal whitespace (it does not - backend only does whole-body `.strip()` at `consumers.py:34`, which is compliant).

- [ ] **Step 3: Verify build and behaviour**

Run: `cd /opt/spt-mentoring/frontend && npx tsc --noEmit && npm run build` - expect success.
Manual: multi-line message with blank lines and runs of spaces survives send -> live WS render -> reload-from-history render identically. Shift+Enter inserts newline on desktop; Enter sends. With DevTools device emulation (touch), Enter inserts a newline and only the button sends.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/MessagesPage.tsx
git commit -m "fix(chat): multi-line auto-growing composer, touch-aware Enter, preserve whitespace in bubbles"
```

---

### Task 2: P1-2 backend guarantee - regression test that whitespace survives the API

**Files:**
- Modify: `backend/apps/messaging/tests.py` (append to existing test classes area)

**Interfaces:**
- Consumes: existing test helpers in `apps/messaging/tests.py` (see `MessageModerationOutcomeTests` setUp at :35 for the matched-pair fixture pattern - copy it).

- [ ] **Step 1: Write the test**

```python
class MessageWhitespaceTests(APITestCase):
    """Internal whitespace and newlines must survive storage and serialization (P1-2)."""

    def setUp(self):
        # Mirror the matched-pair fixture from MessageModerationOutcomeTests
        # (mentor+scholar users, active MentoringMatch, shared Conversation).
        ...  # copy the exact setUp used by MessageModerationOutcomeTests

    def test_internal_whitespace_and_newlines_preserved(self):
        body = 'def f():\n    return  1\n\n\ttabbed'
        self.client.force_authenticate(self.scholar)
        resp = self.client.post('/api/messaging/messages/', {
            'conversation': self.conversation.id, 'body': body,
        })
        self.assertEqual(resp.status_code, 201)
        msg = Message.objects.get(id=resp.data['id'])
        self.assertEqual(msg.body, body)
        list_resp = self.client.get(f'/api/messaging/messages/?conversation={self.conversation.id}')
        bodies = [m['body'] for m in list_resp.data['results']] if 'results' in list_resp.data else [m['body'] for m in list_resp.data]
        self.assertIn(body, bodies)
```

(When writing this for real, replicate the exact setUp fixture and URL style already used in the file - inspect `MessageModerationOutcomeTests` first and reuse its conventions verbatim.)

- [ ] **Step 2: Run it**

Run: `cd backend && python manage.py test apps.messaging -v 1` - expect PASS (behaviour already correct server-side; this is a drift guard).

- [ ] **Step 3: Commit**

```bash
git add backend/apps/messaging/tests.py
git commit -m "test(messaging): guard that internal whitespace and newlines survive the API"
```

---

### Task 3: P1-3 - Mobile chat layout, dvh height, single-pane flow, draft persistence

**Files:**
- Modify: `frontend/src/pages/MessagesPage.tsx` (:272 container, :274 sidebar, :403 thread column, :46 draft state, conversation-select logic)

**Interfaces:**
- Consumes: `IS_COARSE_POINTER`, `taRef` from Task 1.
- Produces: draft persisted per conversation in `sessionStorage` under key `chat-draft-<conversationId>`.

- [ ] **Step 1: Responsive two-pane -> single-pane layout**

Container (:272): replace `h-[calc(100vh-14rem)]` with `h-[calc(100dvh-11rem)] md:h-[calc(100vh-14rem)]` (dvh tracks the visual viewport as the mobile keyboard/browser chrome moves).

Sidebar (:274): `w-72 flex-shrink-0 ...` becomes:

```tsx
className={`w-full md:w-72 md:flex-shrink-0 flex-col ... ${selectedConv ? 'hidden md:flex' : 'flex'}`}
```

Thread column (:403): `flex-1 flex flex-col` becomes:

```tsx
className={`flex-1 min-w-0 flex-col ${selectedConv ? 'flex' : 'hidden md:flex'}`}
```

Add a back button at the start of the thread header, `md:hidden`, with a comfortable touch target:

```tsx
<button
  onClick={() => setSelectedConv(null)}
  className="md:hidden mr-2 p-2 -ml-2 rounded-lg text-navy-500/60 hover:bg-purple-50"
  aria-label="Back to conversations"
>
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
</button>
```

If the page auto-selects the first conversation on load, gate that: only auto-select when `window.innerWidth >= 768`. Mobile users land on the conversation list. Message bubbles (:430): change `max-w-sm` to `max-w-[80%] sm:max-w-sm`. Confirm the outer page does not scroll: the messages area keeps `flex-1 overflow-y-auto overflow-x-hidden`; the composer bar stays inside the flex column so it docks above the keyboard.

- [ ] **Step 2: Per-conversation draft persisted across rotation/reload**

```tsx
const draftKey = (id: number) => `chat-draft-${id}`;
```

- On conversation change (`useEffect` on `selectedConv`): `setDraft(selectedConv ? sessionStorage.getItem(draftKey(selectedConv)) ?? '' : ''); requestAnimationFrame(autoGrow);`
- In the textarea `onChange`: also `if (selectedConv) sessionStorage.setItem(draftKey(selectedConv), e.target.value);`
- In `sendMessage` after `setDraft('')`: `if (selectedConv) sessionStorage.removeItem(draftKey(selectedConv));` (and keep the existing restore-on-failure, which should also restore the storage entry).

sessionStorage survives an orientation-change reload in the same tab, which is exactly Rebecca's failure case.

- [ ] **Step 3: Verify at 360/390/414px**

`npx tsc --noEmit && npm run build`. In device emulation at 360, 390, 414 widths, portrait and landscape: list -> tap conversation -> thread fills viewport, composer visible, no horizontal scroll, back button returns to list; type a draft, reload the page, draft is restored.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/MessagesPage.tsx
git commit -m "fix(chat): mobile-first single-pane layout with dvh sizing and per-conversation draft persistence"
```

---

### Task 4: P1-3 (cont.) + P3-6 - App-wide mobile overflow audit fixes

**Files:**
- Modify: `frontend/src/pages/ForumsPage.tsx` (:363 post body), `frontend/src/components/layout/Layout.tsx` (:243-268 mobile menu), `frontend/src/pages/HomePage.tsx` (:240 stats grid), spot-fixes found during audit in `SessionsPage.tsx`, `GoalsPage.tsx`, `MentorDiscoveryPage.tsx`

**Interfaces:** none.

- [ ] **Step 1: Forum post overflow (P3-6)**

`ForumsPage.tsx:363`: add wrapping so long unbroken strings cannot widen the card:

```tsx
<p className="text-sm text-navy-500/80 whitespace-pre-wrap break-words">{post.body}</p>
```

Also add `min-w-0` to the post card's flex parent if the body sits beside an avatar column (check while editing).

- [ ] **Step 2: NotificationBell reachable on mobile**

`Layout.tsx`: the bell (:31-55) renders only in the desktop user area (:203). Add it next to the burger button (:228) inside the `md:hidden` cluster so mobile users can reach notifications:

```tsx
<div className="flex items-center gap-1 md:hidden">
  <NotificationBell />
  {/* existing burger button */}
</div>
```

- [ ] **Step 3: Sweep remaining pages at 360px**

With device emulation at 360px, walk Home, Find a Mentor, Sessions, Goals, Forums, News, Profile. Fix any horizontal overflow found by adding `break-words`/`min-w-0`/responsive grid classes; known suspects: HomePage stats `grid-cols-2` tiles with long sub-text, SessionsPage `AvailabilityManager` weekly grid, GoalsPage card rows. Keep changes minimal - class-level only.

- [ ] **Step 4: Verify and commit**

`npx tsc --noEmit && npm run build`.

```bash
git add frontend/src/pages/ForumsPage.tsx frontend/src/components/layout/Layout.tsx frontend/src/pages/HomePage.tsx frontend/src/pages/SessionsPage.tsx frontend/src/pages/GoalsPage.tsx frontend/src/pages/MentorDiscoveryPage.tsx
git commit -m "fix(mobile): eliminate horizontal overflow across pages, surface notification bell in mobile header"
```

---

### Task 5: P2-1 backend (a) - Sender sees own held/blocked messages, with a safe reason

**Files:**
- Modify: `backend/apps/messaging/views.py` (:229-239 get_queryset, :327-349 create responses), `backend/apps/messaging/consumers.py` (:60-72 blocked/flagged sends), `backend/apps/moderation/service.py` (new helper), `backend/apps/messaging/tests.py`, `backend/apps/messaging/serializers.py`

**Interfaces:**
- Produces: `ModerationService.sender_facing_reason(result) -> str` returning copy like `'it contains a web link'`, `'it appears to contain contact details'`, or `'it contains wording that is not permitted on the platform'`. Serializer continues to expose `status`; the sender's own `flagged`/`blocked` messages now appear in list responses.

- [ ] **Step 1: Write failing tests**

In `apps/messaging/tests.py`:

```python
class HeldMessageVisibilityTests(APITestCase):
    # fixture: matched pair + conversation, as in MessageModerationOutcomeTests

    def test_sender_sees_own_flagged_message_with_status(self):
        # send a message containing a bare @ so it is held
        resp = self.client.post(..., {'conversation': ..., 'body': 'reach me @ mydomain'})
        self.assertEqual(resp.status_code, 202)
        listing = self.client.get(f'/api/messaging/messages/?conversation={self.conversation.id}')
        statuses = {m['id']: m['status'] for m in ...}
        self.assertIn('flagged', statuses.values())

    def test_recipient_does_not_see_held_message(self):
        # same send, then authenticate as the other participant and assert the
        # flagged message id is absent from their listing
        ...

    def test_block_response_names_category_not_term(self):
        # message hitting a blocked term returns 400 whose detail mentions a
        # reason phrase but never the term itself
        ...
```

Run: `python manage.py test apps.messaging -v 1` - expect the new tests to FAIL.

- [ ] **Step 2: Queryset - sender sees own non-delivered messages**

`views.py` `MessageViewSet.get_queryset` (:229-239): for non-staff, replace the flat `status=DELIVERED` filter with:

```python
from django.db.models import Q
qs = qs.filter(
    Q(status=Message.Status.DELIVERED)
    | Q(sender=user, status__in=[Message.Status.FLAGGED, Message.Status.BLOCKED])
)
```

Update `test_history_excludes_blocked_and_flagged_for_non_staff` (:194) to assert the RECIPIENT still cannot see them while the SENDER now can. Check `ConversationSerializer.get_last_message`/unread counts still filter to DELIVERED only (they do, `models.py:53-62`) so previews do not leak held content.

- [ ] **Step 3: Safe reason helper + response copy**

In `moderation/service.py` add:

```python
@classmethod
def sender_facing_reason(cls, result):
    """A safe, category-level explanation for the sender. Never reveals the term list."""
    note = (result.note or '').lower()
    rules = result.triggered_rules or []
    if any(r.get('match_type') == ModerationTerm.MatchType.URL_FRAGMENT for r in rules):
        return 'it contains a web link'
    if 'email' in note or 'phone' in note or '@' in note or 'contact' in note:
        return 'it appears to contain contact details (such as an email address or phone number)'
    return 'it contains wording that is not permitted on the platform'
```

Wire it into both surfaces:

- `views.py` flagged 202 detail: `f'Your message has been held for review before delivery because {reason}. A moderator will review it shortly and you will be notified of the outcome. You can edit the message to remove the highlighted issue and resend it.'` plus a new key `'moderation_reason': reason` and include the serialised message (`self.get_serializer(message).data`) so the frontend can render the pending bubble immediately.
- blocked 400 detail: `f'Your message could not be sent because {reason}. Please edit it and try again.'` plus `'moderation_reason': reason` and the serialised message.
- `consumers.py` flagged/blocked sends: add `'reason': reason` and `'message_id': message.id` to both event payloads.

- [ ] **Step 4: Run tests green, then full messaging + moderation suites**

`python manage.py test apps.messaging apps.moderation -v 1` - all pass (fix the updated history test).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/messaging/views.py backend/apps/messaging/consumers.py backend/apps/moderation/service.py backend/apps/messaging/tests.py backend/apps/messaging/serializers.py
git commit -m "feat(moderation): senders see their held messages with a category-level reason"
```

---

### Task 6: P2-1 backend (b) - approve() delivers live and tells the sender; fix mark_delivered

**Files:**
- Modify: `backend/apps/moderation/service.py` (:723-739 approve), `backend/apps/messaging/admin.py` (:700-702 mark_delivered), `backend/apps/messaging/tests.py` or `backend/apps/moderation/tests/` (new test file `test_release_path.py`)

**Interfaces:**
- Consumes: channel layer group name `chat_<conversation_id>`; existing `chat_message` event shape.
- Produces: on approve - sender Notification ("Your message has been approved and delivered."), recipient notification via existing post_save signal (unchanged), and a `chat_message` group broadcast so open threads update live.

- [ ] **Step 1: Write failing tests** (`backend/apps/moderation/tests/test_release_path.py`)

```python
class ApproveReleaseTests(TestCase):
    # fixture: matched pair, conversation, one FLAGGED message

    def test_approve_sets_delivered_and_notifies_sender(self):
        ModerationService.approve(self.message, self.admin)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, Message.Status.DELIVERED)
        self.assertTrue(Notification.objects.filter(
            user=self.sender, title__icontains='approved').exists())

    def test_approve_notifies_recipient(self):
        ModerationService.approve(self.message, self.admin)
        self.assertTrue(Notification.objects.filter(user=self.recipient).exists())

    def test_admin_mark_delivered_routes_through_approve(self):
        # call the admin action with a queryset of one flagged message and
        # assert moderated_by is set and a ModerationLog row exists
        ...
```

Run: expect FAIL.

- [ ] **Step 2: Extend `approve()`**

After the existing save + ModerationLog in `service.py:723-739`:

```python
# Tell the sender the outcome (the 202 response promised this).
Notification.objects.create(
    user=message.sender,
    type=Notification.Type.MESSAGE,
    title='Your message has been approved',
    body='Your message has been reviewed and delivered.',
    link='/messages',
)
# Push the released message into any open thread.
channel_layer = get_channel_layer()
if channel_layer is not None:
    async_to_sync(channel_layer.group_send)(
        f'chat_{message.conversation_id}',
        {
            'type': 'chat_message',
            'message_id': message.id,
            'body': message.body,
            'sender_id': message.sender_id,
            'sender_name': message.sender.get_full_name(),
            'sent_at': message.sent_at.isoformat(),
        },
    )
```

Use the exact field/name conventions already in `consumers.py:75-85` (check `sender_name` derivation there and mirror it). Recipient notification + debounced email already fire via the post_save signal when status flips to delivered - do not duplicate.

- [ ] **Step 3: Fix `mark_delivered`**

`admin.py:700-702`: replace `queryset.update(status=...)` with a loop calling `ModerationService.approve(message, request.user, notes='Bulk approved via admin')`, so audit fields, logs, notifications, and the broadcast all happen.

- [ ] **Step 4: Green + regression suites**

`python manage.py test apps.moderation apps.messaging -v 1` - all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/moderation/service.py backend/apps/messaging/admin.py backend/apps/moderation/tests/test_release_path.py
git commit -m "fix(moderation): approving a held message notifies the sender and delivers live over WebSocket"
```

---

### Task 7: P2-1 frontend - pending/blocked bubbles with reason, live release

**Files:**
- Modify: `frontend/src/pages/MessagesPage.tsx` (WS handlers :148-170, moderationNotice :505-517, bubble render :425-484, sendMessage :192-221), `frontend/src/types/index.ts` (Message type gains `moderation_reason?`)

**Interfaces:**
- Consumes: Task 5's 202/400 payloads (serialised message + `moderation_reason`), WS `message_flagged`/`message_blocked` now carrying `reason` and `message_id`; Task 6's `chat_message` broadcast on release.

- [ ] **Step 1: Render own held/blocked messages as bubbles with badges**

History now includes them (Task 5). In the bubble, after the body, when `isMine`:

```tsx
{msg.status === 'flagged' && (
  <span className="inline-flex items-center gap-1 mt-1 text-[10px] font-medium text-amber-600">
    <svg className="w-3 h-3" ...clock icon... /> Pending review
  </span>
)}
{msg.status === 'blocked' && (
  <span className="... text-red-600">Not delivered</span>
)}
```

On a 202/400 REST response, append the serialised message from the response body to local state so the pending/blocked bubble appears instantly; keep the banner (`moderationNotice`) and include the reason from `moderation_reason`, e.g. "Held for review because it contains a web link. A moderator will check it shortly.". WS `message_flagged`/`message_blocked` handlers likewise use `data.reason` when present.

- [ ] **Step 2: Handle live release**

The existing `chat_message` handler already appends broadcast messages; add dedup by `message_id` against messages already in state, and when the released id matches an existing `flagged` bubble, replace it (status -> delivered) instead of appending a duplicate.

- [ ] **Step 3: Verify + commit**

`npx tsc --noEmit && npm run build`; manual: send `test @ contact` -> pending bubble + reason banner; approve in admin -> bubble flips to delivered live (or on refetch), sender gets the in-app notification.

```bash
git add frontend/src/pages/MessagesPage.tsx frontend/src/types/index.ts
git commit -m "feat(chat): pending-review and not-delivered states visible to the sender with a clear reason"
```

---

### Task 8: P2-2 backend - ZIP + document types, one validator for chat and forums

**Files:**
- Modify: `backend/apps/users/validators.py` (:4-46), `backend/apps/forums/serializers.py` (attachment field), `backend/apps/forums/views.py` (post create - attachment passthrough already works via serializer), `backend/apps/messaging/views.py` (:355-375 broadcast payload)
- Test: `backend/apps/users/tests/` (validator tests), `backend/apps/forums/tests.py` (forum attachment accept/reject)

**Interfaces:**
- Produces: `ALLOWED_ATTACHMENT_TYPES` gains `application/zip`, `application/x-zip-compressed`; `_EXT_TO_MIME` gains `'.zip'`. `validate_message_attachment` reused by forums (rename NOT needed; import as-is). REST broadcast gains `attachment_url` and `attachment_name` keys.

- [ ] **Step 1: Failing tests**

Validator tests: ZIP under 20 MB passes; `.exe` (`application/x-msdownload`) and `.js` rejected; oversize rejected. Forum test: multipart POST to posts endpoint with a small ZIP + clean body -> 201 and `attachment` URL present in response; `.exe` -> 400.

- [ ] **Step 2: Extend the validator and wire it into forums**

`users/validators.py`: add the two ZIP MIME types to `ALLOWED_ATTACHMENT_TYPES`, `'.zip': 'application/zip'` to `_EXT_TO_MIME`, and update the error copy to '...an image, PDF, Word document, Excel, PowerPoint, CSV, text or ZIP file.'.

`forums/serializers.py`: declare the field explicitly:

```python
attachment = serializers.FileField(
    validators=[validate_message_attachment], required=False, allow_null=True)
```

- [ ] **Step 3: Broadcast attachment metadata on REST-created chat messages**

`messaging/views.py` (:355-375): add to the group_send payload:

```python
'attachment_url': message.attachment.url if message.attachment else None,
'attachment_name': message.attachment_name or (message.body if message.attachment else ''),
```

- [ ] **Step 4: Green + commit**

`python manage.py test apps.users apps.forums apps.messaging -v 1`.

```bash
git add backend/apps/users/validators.py backend/apps/forums/serializers.py backend/apps/messaging/views.py backend/apps/users/tests backend/apps/forums/tests.py
git commit -m "feat(attachments): allow ZIP, share one validator between chat and forum attachments"
```

---

### Task 9: P2-2 frontend - forum uploads, chat error surfacing, live attachment render

**Files:**
- Modify: `frontend/src/pages/ForumsPage.tsx` (reply form :371-409, post render :363), `frontend/src/pages/MessagesPage.tsx` (sendAttachment :223-237, WS chat_message handler :151-157, file accept :528, sidebar preview :357-359)

**Interfaces:**
- Consumes: Task 8's broadcast `attachment_url`/`attachment_name`; forum serializer `attachment` field.

- [ ] **Step 1: Forum attachment upload + display**

Reply form: add a paperclip file input (`accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip"`), post via FormData (`thread`, `body`, `attachment`). Show the chosen filename next to the button before submit. On post render, when `post.attachment`, render the same link-with-paperclip pattern as chat bubbles (copy from MessagesPage :439-450, keep `break-words`).

- [ ] **Step 2: Chat - surface rejection, render live attachments, indicate presence**

- `sendAttachment`: add `.catch(err => setModerationNotice({tone:'error', text: err.response?.data?.attachment?.[0] ?? 'That file could not be attached.'}))` (match the actual notice-state shape in the file).
- Chat `accept` attr: add `.zip`.
- WS `chat_message` handler: use `data.attachment_url`/`data.attachment_name` when present instead of hardcoding `attachment: null`.
- Sidebar conversation preview: when `last_message` body equals an attachment filename it already shows the name; prepend a paperclip glyph when `last_message.attachment` is truthy if the serializer exposes it - if not exposed, skip (do not widen the serializer for this nicety; the in-thread indicator satisfies the requirement).

- [ ] **Step 3: Verify + commit**

Build + manual: ZIP sends in chat and forum; recipient sees it live without refetch; a `.exe` shows a clear error banner instead of failing silently.

```bash
git add frontend/src/pages/ForumsPage.tsx frontend/src/pages/MessagesPage.tsx
git commit -m "feat(attachments): forum uploads, ZIP support in chat UI, live attachment delivery and upload errors surfaced"
```

---

### Task 10: P2-3 (a) - Match/assignment email

**Files:**
- Modify: `backend/apps/users/signals.py` (:56-143), `backend/apps/messaging/tasks.py` (new task `send_match_notification_emails`), `backend/apps/notifications/email_catalogue.py` (new `EmailSpec`)
- Test: `backend/apps/users/tests/` (new `test_match_emails.py`)

**Interfaces:**
- Produces: Celery task `send_match_notification_emails(match_id)`; catalogue key `match_assigned` whose subject contains 'You have been matched' (classifiable by `infer_category` - add matcher).

- [ ] **Step 1: Failing tests**

```python
class MatchEmailTests(TestCase):
    def test_match_creation_sends_named_emails_to_both_parties(self):
        # create MentoringMatch with CELERY_TASK_ALWAYS_EAGER=True override
        # assert len(mail.outbox) == 2
        # scholar email body contains mentor full name and FRONTEND_URL + '/messages'
        # mentor email body contains scholar full name
    def test_match_email_respects_notification_preference(self):
        # scholar.notification_email = False -> only mentor emailed
```

- [ ] **Step 2: Task + wiring**

In `messaging/tasks.py` (keeps email tasks together with the other reminder tasks):

```python
MATCH_EMAIL_SUBJECT = 'SPT Mentoring - You have been matched'

@shared_task
def send_match_notification_emails(match_id):
    from apps.users.models import MentoringMatch
    match = MentoringMatch.objects.select_related('mentor', 'scholar').filter(id=match_id).first()
    if match is None or not match.is_active:
        return
    link = f'{settings.FRONTEND_URL}/messages'
    pairs = [
        (match.scholar, match.mentor, 'mentor'),
        (match.mentor, match.scholar, 'scholar'),
    ]
    for recipient, other, other_role in pairs:
        if not (recipient.notification_email and recipient.email):
            continue
        send_mail(
            MATCH_EMAIL_SUBJECT,
            (
                f'Hi {recipient.first_name},\n\n'
                f'You have been matched with your {other_role}, {other.get_full_name()}, '
                'on the SPT Arkwright Mentoring Platform.\n\n'
                f'Send them a message to introduce yourself: {link}\n\n'
                'Best regards,\nSPT Mentoring Team'
            ),
            settings.DEFAULT_FROM_EMAIL,
            [recipient.email],
            fail_silently=True,
        )
```

In `users/signals.py` `ensure_match_conversation`, after the in-app notifications for a NEW active match (and reinstatement), add `send_match_notification_emails.delay(instance.id)` (import lazily inside the function to avoid app-loading cycles). Add the catalogue `EmailSpec` (key `match_assigned`, trigger 'MentoringMatch created or reinstated', audience 'Matched mentor and scholar') and a matcher `('You have been matched', 'match_assigned')` in `_CATEGORY_MATCHERS`; run `python manage.py sync_email_catalogue` at deploy.

- [ ] **Step 3: Green + commit**

`python manage.py test apps.users apps.notifications -v 1`.

```bash
git add backend/apps/messaging/tasks.py backend/apps/users/signals.py backend/apps/notifications/email_catalogue.py backend/apps/users/tests/test_match_emails.py
git commit -m "feat(notifications): email both parties with names and a direct link when a match is made"
```

---

### Task 11: P2-3 (b) - Forum reply notifications

**Files:**
- Modify: `backend/apps/forums/services.py` (new function `notify_thread_participants_of_reply`), `backend/apps/forums/signals.py`, `backend/apps/notifications/emails.py` (:27-30 EMAILABLE_TYPES)
- Test: `backend/apps/forums/test_scholar_post_notifications.py` (extend) or new `backend/apps/forums/test_reply_notifications.py`

**Interfaces:**
- Consumes: `queue_notification_email` from `apps/notifications/digest.py`; `Notification.Type.FORUM_REPLY` (exists, unused); `Post.mentor_notified` once-only pattern (`services.py:35-40`).
- Produces: on a post becoming VISIBLE in a thread, every prior participant of that thread (thread creator + authors of earlier VISIBLE posts, excluding the new author) with forum visibility gets a FORUM_REPLY notification + debounced email.

- [ ] **Step 1: Failing tests**

- reply by mentor in a thread a scholar started -> scholar notified (type FORUM_REPLY) and email queued;
- author of the reply not notified;
- fires once even if the post is saved again (reuse the atomic claim pattern - add a `participants_notified` BooleanField to Post OR reuse `mentor_notified` semantics with a second field; a new field needs a migration);
- user without visibility of the forum not notified; preference `notification_email=False` still gets the in-app notification but no email (that split already lives inside `queue_notification_email`).

- [ ] **Step 2: Implement**

Add `participants_notified = models.BooleanField(default=False)` to `Post` (**migration needed**: `python manage.py makemigrations forums`). New service function modelled directly on `notify_mentors_of_scholar_post` (:24-74): atomic once-only claim, recipients =

```python
authors = set(thread.posts.filter(status=Post.Status.VISIBLE).exclude(author=post.author).values_list('author_id', flat=True))
authors.add(thread.created_by_id)
authors.discard(post.author_id)
```

filtered by active users with visibility of `thread.forum` (reuse the visibility scoping used at :54-56). Notification: type `FORUM_REPLY`, title `'New reply in "{thread.title}"'`, body `post.body[:100]`, link `/forums?thread={thread.id}`; then `queue_notification_email(notification)`. Call it from the same signal path that calls the scholar-post notifier (`forums/signals.py:11-14`), for every newly VISIBLE post. Add `Notification.Type.FORUM_REPLY` to `EMAILABLE_TYPES` (`emails.py:27-30`) and make sure `send_notification_email`'s subject/body handling covers the new type (inspect `emails.py:41-75` and extend its subject map; add a catalogue spec + matcher like Task 10).

Keep the existing scholar-post -> matched-mentor path untouched; dedupe so a matched mentor who is also a thread participant gets one notification, not two (skip FORUM_REPLY for users who just received SCHOLAR_FORUM_POST for the same post).

- [ ] **Step 3: Green + migrate + commit**

`python manage.py test apps.forums apps.notifications -v 1`.

```bash
git add backend/apps/forums/services.py backend/apps/forums/signals.py backend/apps/forums/models.py backend/apps/forums/migrations backend/apps/notifications/emails.py backend/apps/notifications/email_catalogue.py backend/apps/forums/test_reply_notifications.py
git commit -m "feat(notifications): notify thread participants of forum replies with debounced email"
```

---

### Task 12: P2-3 (c) - Name the partner and link the platform in reminder emails

**Files:**
- Modify: `backend/apps/messaging/tasks.py` (:11-17 subject/body builder, :138-169 task)
- Test: `backend/apps/messaging/tests.py` (or wherever `send_no_contact_reminders` is currently tested - check first and extend there)

**Interfaces:**
- Produces: `build_no_contact_body(first_name, partner_name, partner_role)`.

- [ ] **Step 1: Failing test** - reminder email body contains the partner's full name, their role word ('mentor'/'scholar'), and `settings.FRONTEND_URL`.

- [ ] **Step 2: Implement**

```python
def build_no_contact_body(first_name, partner_name, partner_role):
    return (
        f'Hi {first_name},\n\n'
        f'It looks like you and your {partner_role}, {partner_name}, have not been in touch recently '
        'on the SPT Arkwright Mentoring Platform.\n\n'
        f'Send them a message here: {settings.FRONTEND_URL}/messages\n\n'
        'Best regards,\nSPT Mentoring Team'
    )
```

Update the call sites in `send_no_contact_reminders` to pass the counterpart's name/role for each member of the pair. Check the sponsor update reminder (:172-206) for the same ambiguity and apply the same treatment if its copy is generic.

- [ ] **Step 3: Green + commit**

```bash
git add backend/apps/messaging/tasks.py backend/apps/messaging/tests.py
git commit -m "fix(email): reminder emails name the mentoring partner and link to the platform"
```

---

### Task 13: P2-4 backend - Edit messages with re-moderation; close the PATCH holes

**Files:**
- Modify: `backend/apps/messaging/models.py` (add `edited_at`), `backend/apps/messaging/serializers.py` (expose `edited_at`), `backend/apps/messaging/views.py` (custom `partial_update`, restrict methods), `backend/apps/forums/views.py` (PostViewSet ownership + re-moderation on update), `backend/apps/forums/serializers.py` (expose `updated_at` or add `edited_at`)
- Test: `backend/apps/messaging/tests.py` (new `MessageEditTests`), `backend/apps/forums/tests.py` (new `PostEditTests`)
- **Migration needed:** `messaging` (edited_at), possibly `forums` if adding `edited_at`

**Interfaces:**
- Produces: `PATCH /api/messaging/messages/<id>/` with `{'body': str}` - sender only; allowed when status is `flagged`/`blocked` (any time) or `delivered` within 15 minutes of `sent_at`; re-runs `ModerationService.screen`; returns the same 201/202/400-style envelope as create; broadcasts `{'type': 'message_edited', 'message_id', 'body', 'edited_at'}` plus a `chat_message`-equivalent update when the edit delivers. `Message.edited_at` (DateTimeField null). `MessageViewSet.http_method_names = ['get', 'post', 'patch', 'head', 'options']`.

- [ ] **Step 1: Failing tests**

`MessageEditTests`: sender edits own delivered message within window -> 200, body updated, `edited_at` set, re-screened (edit it to contain a blocked term -> becomes blocked + 400 envelope); sender edits own FLAGGED message to clean text -> delivered + broadcast; editing ANOTHER user's message -> 403/404; editing after 15 minutes (freeze time or backdate `sent_at` via queryset update) -> 403; PUT and DELETE -> 405; history row recorded (`message.history.count()` grows - HistoricalRecords is the audit trail).
`PostEditTests`: author edits own post -> re-screened (clean -> visible; profanity -> flagged 202); non-author PATCH -> 403; `updated_at`/edited marker exposed.

- [ ] **Step 2: Implement messaging edit**

Model: `edited_at = models.DateTimeField(null=True, blank=True)`; `python manage.py makemigrations messaging`. Serializer: add `'edited_at'` to fields (read-only). Views:

```python
MESSAGE_EDIT_WINDOW = timedelta(minutes=15)

http_method_names = ['get', 'post', 'patch', 'head', 'options']

def partial_update(self, request, *args, **kwargs):
    message = self.get_object()
    if message.sender_id != request.user.id:
        return Response({'detail': 'You can only edit your own messages.'}, status=403)
    if message.conversation.conversation_type == Conversation.Type.MASS_MESSAGE:
        return Response({'detail': 'Broadcast messages cannot be edited.'}, status=403)
    if message.status == Message.Status.DELIVERED and timezone.now() - message.sent_at > MESSAGE_EDIT_WINDOW:
        return Response({'detail': 'Messages can only be edited within 15 minutes of sending.'}, status=403)
    if message.status not in (Message.Status.DELIVERED, Message.Status.FLAGGED, Message.Status.BLOCKED):
        return Response({'detail': 'This message cannot be edited.'}, status=403)
    body = (request.data.get('body') or '').strip()
    if not body:
        return Response({'detail': 'Message body cannot be empty.'}, status=400)
    message.body = body
    message.edited_at = timezone.now()
    message.status = Message.Status.PENDING
    message.save()
    result = ModerationService.screen(message)
    # reuse the exact blocked/flagged/delivered response + broadcast logic from create();
    # factor that logic into a private _moderation_response(message, result) helper used by both,
    # with the delivered branch here broadcasting a 'message_edited' event so open
    # threads replace the bubble body rather than appending.
```

(Match the real `Conversation` type enum name when editing - check `models.py:132` area for how mass-message conversations are typed.) Check `screen()` -> post_save signal behaviour: flipping an edited message back to delivered re-fires `notify_recipients_on_delivered_message`, which would re-notify. Suppress duplicate notifications for edits by checking `instance.edited_at` in the signal guard and skipping notification creation when the edit did not change status from non-delivered to delivered - simplest correct rule: in the signal, skip when `instance.edited_at is not None and instance.status == 'delivered'` unless a previous flagged/blocked state existed (pass through an attribute set in `partial_update`, e.g. `message._was_held = old_status != Message.Status.DELIVERED`, and only notify when `_was_held`).

- [ ] **Step 3: Implement forum post edit protection**

`PostViewSet`: add

```python
def get_permissions(self):
    return [IsAuthenticated()]

def partial_update(self, request, *args, **kwargs):
    post = self.get_object()
    if post.author_id != request.user.id and not request.user.is_staff:
        return Response({'detail': 'You can only edit your own posts.'}, status=403)
    body = (request.data.get('body') or '').strip()
    if not body:
        return Response({'detail': 'Post body cannot be empty.'}, status=400)
    post.body = body
    post.status = Post.Status.PENDING
    post.save(update_fields=['body', 'status'])
    result = ModerationService.screen_text(post.body)
    # apply the same status mapping + response envelope as create()
    # (factor create()'s outcome handling into a helper and call it from both)
```

Also restrict `http_method_names` to exclude PUT/DELETE (or add matching guards to `update`/`destroy`). Expose `updated_at` in the Post serializer for the edited marker (Post already has `updated_at` via auto_now if present - verify; if absent, add `edited_at` + migration).

- [ ] **Step 4: Green + full regression**

`python manage.py test apps.messaging apps.forums apps.moderation -v 1` - all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/messaging/models.py backend/apps/messaging/migrations backend/apps/messaging/serializers.py backend/apps/messaging/views.py backend/apps/forums/views.py backend/apps/forums/serializers.py backend/apps/messaging/tests.py backend/apps/forums/tests.py
git commit -m "feat(messaging): sender can edit messages with re-moderation; close unmoderated PATCH holes in chat and forums"
```

---

### Task 14: P2-4 frontend - Edit UI in chat and forums

**Files:**
- Modify: `frontend/src/pages/MessagesPage.tsx`, `frontend/src/pages/ForumsPage.tsx`, `frontend/src/types/index.ts`

**Interfaces:**
- Consumes: Task 13's PATCH endpoints and `edited_at`; WS `message_edited` event.

- [ ] **Step 1: Chat edit flow**

On own bubbles (delivered within ~15 min by client clock, or flagged/blocked), show a small "Edit" affordance (pencil icon button, min 40px touch target). Editing loads the body into the composer in an "editing" mode (banner above composer: "Editing message - Cancel"); send PATCHes instead of POSTing; handle the same 202/400 envelopes as sending (Task 7 banners). Render `(edited)` in the bubble meta when `msg.edited_at`. Handle WS `message_edited` by replacing the matching message body in state.

- [ ] **Step 2: Forum edit flow**

"Edit" on own posts loads body into the reply textarea in edit mode; PATCH; show pending/blocked notices per the existing `postNotice` pattern (:233, :268-290); show "(edited)" when `updated_at` is meaningfully later than the created timestamp (or `edited_at` if that field was added).

- [ ] **Step 3: Verify + commit**

Build + manual: trip moderation, edit the held message from its bubble, resend clean, watch it deliver.

```bash
git add frontend/src/pages/MessagesPage.tsx frontend/src/pages/ForumsPage.tsx frontend/src/types/index.ts
git commit -m "feat(chat,forums): edit own messages and posts, including held ones, with edited markers"
```

---

### Task 15: P3-1 - Dates in chat

**Files:**
- Modify: `frontend/src/pages/MessagesPage.tsx` (:425 map, :456-458 timestamp)

- [ ] **Step 1:** In the message map, insert a day separator whenever `msg.sent_at` falls on a different calendar day from the previous message:

```tsx
const dayLabel = (iso: string) => {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
};
```

Separator row: centred pill `bg-purple-50 text-navy-500/50 text-[11px] rounded-full px-3 py-1`. Add a full date-time tooltip on the timestamp: `title={new Date(msg.sent_at).toLocaleString('en-GB')}`.

- [ ] **Step 2:** Build, verify, commit.

```bash
git add frontend/src/pages/MessagesPage.tsx
git commit -m "feat(chat): day separators and full-date hover on message timestamps"
```

---

### Task 16: P3-2 - Expandable mentor descriptions

**Files:**
- Modify: `frontend/src/pages/MentorDiscoveryPage.tsx` (:141-146)

- [ ] **Step 1:** Track expansion per card (`const [expandedBios, setExpandedBios] = useState<Set<number>>(new Set())`). Replace the clamped bio with:

```tsx
<p className={`mt-3 text-xs text-navy-500/70 leading-relaxed whitespace-pre-wrap break-words ${expandedBios.has(mentor.id) ? '' : 'line-clamp-2'}`}>
  {mentor.bio}
</p>
{mentor.bio.length > 120 && (
  <button onClick={() => toggleBio(mentor.id)} className="mt-1 text-xs font-medium text-pink-500 hover:underline">
    {expandedBios.has(mentor.id) ? 'Show less' : 'Read more'}
  </button>
)}
```

- [ ] **Step 2:** Build, verify, commit.

```bash
git add frontend/src/pages/MentorDiscoveryPage.tsx
git commit -m "feat(discovery): read-more toggle for truncated mentor descriptions"
```

---

### Task 17: P3-3 (a) - Scholar can cancel a pending session request

**Files:**
- Modify: `frontend/src/pages/SessionsPage.tsx` (:247-252)

- [ ] **Step 1:** Change the gate so scholars can withdraw pending requests (backend already permits it):

```tsx
{session.status !== 'completed' && session.status !== 'cancelled' && (
  <button onClick={() => onAction(session.id, 'cancel')} ...>
    {session.status === 'pending' ? 'Withdraw request' : 'Cancel session'}
  </button>
)}
```

Keep mentor Confirm/Decline on pending untouched.

- [ ] **Step 2:** Build, verify (scholar sees Withdraw on pending; mentor flow unchanged), commit.

```bash
git add frontend/src/pages/SessionsPage.tsx
git commit -m "fix(sessions): scholars can withdraw a pending session request"
```

---

### Task 18: P3-3 (b) - Merge overlapping availability windows

**Files:**
- Modify: `backend/apps/sessions/views.py` (slot creation viewset - find the `AvailabilitySlot` viewset's `perform_create`), `backend/apps/sessions/models.py` if a helper fits better
- Test: `backend/apps/sessions/tests.py` (check filename first; create if absent)

- [ ] **Step 1: Failing test** - creating a slot 10:00-11:00 when an unbooked 10:30-11:30 exists for the same mentor results in ONE slot 10:00-11:30; booked slots are never merged; non-overlapping slots untouched.

- [ ] **Step 2: Implement** in the slot viewset's `perform_create`:

```python
def perform_create(self, serializer):
    slot = serializer.save(mentor=self.request.user)
    overlapping = AvailabilitySlot.objects.filter(
        mentor=slot.mentor, is_booked=False,
        start_time__lte=slot.end_time, end_time__gte=slot.start_time,
    ).exclude(id=slot.id)
    if overlapping.exists():
        slot.start_time = min([slot.start_time] + [s.start_time for s in overlapping])
        slot.end_time = max([slot.end_time] + [s.end_time for s in overlapping])
        slot.save(update_fields=['start_time', 'end_time'])
        overlapping.delete()
```

(Adapt names to the real viewset; wrap in `transaction.atomic()`.)

- [ ] **Step 3:** `python manage.py test apps.sessions -v 1` green; commit.

```bash
git add backend/apps/sessions/views.py backend/apps/sessions/tests.py
git commit -m "fix(sessions): merge overlapping unbooked availability windows on creation"
```

---

### Task 19: P3-3 (c) - Mentor proposes a session directly

**Files:**
- Modify: `backend/apps/sessions/views.py` (new `propose` action on the session viewset), `backend/apps/sessions/serializers.py` if needed, `frontend/src/pages/SessionsPage.tsx` (mentor-side "Propose a session" form)
- Test: `backend/apps/sessions/tests.py`

**Interfaces:**
- Produces: `POST /api/sessions/sessions/propose/` `{scholar: id, start_time, end_time, title, agenda}` - mentor only, scholar must be actively matched to the mentor; creates a booked `AvailabilitySlot` + `MentoringSession(status=PENDING, proposed_by_mentor=True?)` - avoid a schema change: reuse PENDING and let the existing role asymmetry decide who confirms. The `confirm` action must allow the SCHOLAR to confirm a mentor-proposed session: simplest rule - allow either party who is not the session creator to confirm. Inspect `confirm` (:103-110) and `perform_create` (:85-92) to find how the creator is recorded; if it is not recorded, add `created_by` FK (**migration**) so "the other party confirms" is enforceable.

- [ ] **Step 1: Failing tests** - mentor proposes to a matched scholar -> 201, session pending, slot booked; proposing to an unmatched scholar -> 403; scholar confirms -> confirmed; mentor cannot confirm their own proposal.

- [ ] **Step 2: Implement** the action + `created_by` field (migration) + confirm-rule change; notify the scholar in-app via the `_notify()` helper (:16-28) with copy 'Your mentor has proposed a session - review and confirm.'.

- [ ] **Step 3: Frontend** - mentor's Sessions view gets a "Propose a session" button opening a small form (scholar select from their active matches, date, start/end time, title, agenda) posting to the action; scholar sees Confirm/Decline on sessions they did not create (mirror the existing mentor pending controls at :229-240).

- [ ] **Step 4:** Tests green, build passes, commit.

```bash
git add backend/apps/sessions/views.py backend/apps/sessions/serializers.py backend/apps/sessions/models.py backend/apps/sessions/migrations backend/apps/sessions/tests.py frontend/src/pages/SessionsPage.tsx
git commit -m "feat(sessions): mentors can propose a session at a specific date and time for scholar confirmation"
```

---

### Task 20: P3-3 (d) - Make the video call link findable

**Files:**
- Modify: `frontend/src/pages/SessionsPage.tsx` (:207-228)

- [ ] **Step 1:** On confirmed sessions OUTSIDE the join window, render the button disabled with explanatory text instead of hiding it:

```tsx
{session.status === 'confirmed' && !isJoinable && (
  <button disabled className="... opacity-50 cursor-not-allowed" title="The join link becomes active 5 minutes before the session starts">
    Join video call (available 5 minutes before start)
  </button>
)}
```

Keep the active button exactly as-is inside the window.

- [ ] **Step 2:** Build, verify, commit.

```bash
git add frontend/src/pages/SessionsPage.tsx
git commit -m "fix(sessions): video call join button always visible on confirmed sessions with availability hint"
```

---

### Task 21: P3-4 - Goal sorting and date labels

**Files:**
- Modify: `frontend/src/pages/GoalsPage.tsx` (fetch :273-276, form :225-261, milestone input :209-210)

- [ ] **Step 1: Sort control** - add a small select ('Newest first' default, 'Due date (soonest)' -> append `&ordering=due_date`, 'Due date (latest)' -> `&ordering=-due_date`) to the list header; wire the value into the react-query key + URL. Backend already supports `ordering_fields = ['created_at', 'due_date']` (`goals/views.py:12-15`) - no backend change.

- [ ] **Step 2: Labels** - wrap the bare date inputs with explicit labels:

```tsx
<label className="block text-xs font-medium text-navy-500/70 mb-1">
  Target completion date
  <input type="date" ... />
</label>
```

Same for the milestone due date ('Milestone due date'). There is no start-date field on the model - the label removes Elizabeth's ambiguity by naming the single date explicitly.

- [ ] **Step 3:** Build, verify sorting round-trips, commit.

```bash
git add frontend/src/pages/GoalsPage.tsx
git commit -m "feat(goals): sort by due date and label date fields clearly"
```

---

### Task 22: P3-5 + P3-7 - Discoverability: shared documents and change password

**Files:**
- Modify: `frontend/src/pages/MessagesPage.tsx` (thread header), `frontend/src/pages/HomePage.tsx` (quick links), `frontend/src/pages/ProfilePage.tsx` (anchor id), `frontend/src/components/layout/Layout.tsx` (user menu if one exists)

- [ ] **Step 1: Shared documents** - add a "Shared documents" link in the chat thread header (icon + label, links to `/profile#documents`) and a quick-link card on the dashboard. Add `id="documents"` to the shared-documents section in ProfilePage and `id="security"` to `SecuritySection`; on mount, scroll to `window.location.hash`. Note in the round summary that full consolidation into a mentor hub is raised as a structural decision.

- [ ] **Step 2: Change password** - ensure the Profile page section heading reads "Security - change your password" and add a "Change password" entry in the header user menu (or next to Sign out in both desktop and mobile menus) linking to `/profile#security`.

- [ ] **Step 3:** Build, verify anchors scroll, commit.

```bash
git add frontend/src/pages/MessagesPage.tsx frontend/src/pages/HomePage.tsx frontend/src/pages/ProfilePage.tsx frontend/src/components/layout/Layout.tsx
git commit -m "feat(nav): make shared documents and change-password directly reachable"
```

---

### Task 23: P3-8 + decision groundwork - Astronautics, list alignment, Baillie investigation

**Files:**
- Modify: `frontend/src/pages/ProfilePage.tsx` (:66-69), `frontend/src/pages/MentorDiscoveryPage.tsx` (:38-41), `backend/apps/users/admin.py` (three constant sites ~:33-44, ~:225-228, ~:305-310)

- [ ] **Step 1:** Add `'Astronautics'` (alphabetical position, before 'Biomedical') to all four lists and fix the MentorDiscoveryPage drift by making its list identical to ProfilePage's (adds the missing 'Structural' too). Keep 'Other' last everywhere.

- [ ] **Step 2:** Baillie investigation (production, read-only):

```bash
docker compose exec backend python manage.py shell -c "
from apps.users.models import User, MentoringMatch
from apps.messaging.models import Conversation
u = User.objects.filter(last_name__icontains='Baillie').first()
print(u and (u.id, u.email, u.role))
print(list(MentoringMatch.objects.filter(scholar=u).values('id','mentor__email','is_active')))
print(list(Conversation.objects.filter(participants=u).values('id','conversation_type')))
"
```

Record the result in the round summary under Decisions needed item 3 (expected outcome: missing/inactive match row or missing conversation - a data fix for the owner, not code).

- [ ] **Step 3:** Build + backend admin loads; commit.

```bash
git add frontend/src/pages/ProfilePage.tsx frontend/src/pages/MentorDiscoveryPage.tsx backend/apps/users/admin.py
git commit -m "feat(profile): add Astronautics discipline and align discipline lists across the app"
```

---

### Task 24: Rich text for News and Mass messages - backend editor + sanitisation

**Files:**
- Modify: `backend/requirements.txt` (add `django-tinymce`, `nh3`), `backend/config/settings.py` (INSTALLED_APPS + `TINYMCE_DEFAULT_CONFIG`), `backend/apps/news/admin.py` (:36-66), `backend/apps/messaging/admin.py` (MassMessageAdmin :744+), new `backend/apps/news/sanitiser.py` (shared helper - import from messaging too)
- Test: new `backend/apps/news/tests.py` additions (sanitiser unit tests)
- **No model migration** - bodies stay `TextField`, now holding sanitised HTML.

**Interfaces:**
- Produces: `sanitise_rich_text(html) -> str` in `apps/news/sanitiser.py`; both admin forms clean `body` through it.

- [ ] **Step 1: Failing sanitiser tests**

`<script>alert(1)</script>` stripped; `onclick` attributes stripped; `<b>/<i>/<ul>/<ol>/<li>/<a href=https>/<span style="color: #ff0000">` kept; `javascript:` hrefs removed; `style` values other than `color` dropped; plain text passes through unchanged.

- [ ] **Step 2: Implement**

```python
import nh3, re

_ALLOWED_TAGS = {'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'a', 'span'}
_ALLOWED_ATTRS = {'a': {'href', 'rel', 'target'}, 'span': {'style'}}
_COLOR_RE = re.compile(r'^\s*color\s*:\s*(#[0-9a-fA-F]{3,8}|rgb\([\d\s,]+\)|[a-zA-Z]+)\s*;?\s*$')

def _attr_filter(tag, attr, value):
    if attr == 'style':
        return value if _COLOR_RE.match(value) else None
    return value

def sanitise_rich_text(html):
    if not html:
        return html
    return nh3.clean(
        html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS,
        url_schemes={'http', 'https', 'mailto'},
        link_rel='noopener noreferrer', attribute_filter=_attr_filter,
    )
```

Settings: add `'tinymce'` to INSTALLED_APPS and

```python
TINYMCE_DEFAULT_CONFIG = {
    'menubar': False,
    'plugins': 'lists link',
    'toolbar': 'bold italic underline forecolor | bullist numlist | link | removeformat',
    'branding': False,
    'height': 320,
}
```

Admin: `NewsItemAdmin` and `MassMessageAdmin` get ModelForms overriding the `body` widget with `tinymce.widgets.TinyMCE` and a `clean_body` returning `sanitise_rich_text(self.cleaned_data['body'])`. Add `pip install django-tinymce nh3` to the deploy notes (requirements pinned to current stable versions). Include TinyMCE static via `python manage.py collectstatic` at deploy; check jazzmin compatibility by loading both admin forms.

- [ ] **Step 3: Mass message email becomes HTML with plain fallback**

`messaging/tasks.py` mass send (:120-126): pass `html_message=mass_message.body` and plain body `django.utils.html.strip_tags(mass_message.body)`.

- [ ] **Step 4:** `python manage.py test apps.news apps.messaging -v 1` green; both admin forms load with the editor and a `<script>` in the body is stripped on save. Commit.

```bash
git add backend/requirements.txt backend/config/settings.py backend/apps/news/admin.py backend/apps/news/sanitiser.py backend/apps/news/tests.py backend/apps/messaging/admin.py backend/apps/messaging/tasks.py
git commit -m "feat(admin): rich text editing with strict HTML sanitisation for news articles and mass messages"
```

---

### Task 25: Rich text - frontend rendering

**Files:**
- Create: `frontend/src/components/ui/RichText.tsx`
- Modify: `frontend/src/pages/NewsArticlePage.tsx` (:96-98), `frontend/src/pages/MessagesPage.tsx` (announcement bubbles ~:449-452), `frontend/src/index.css` (rich-text element styles)

**Interfaces:**
- Produces: `<RichText body={string} className? />` - renders backend-sanitised HTML when the body looks like HTML, else plain text with `whitespace-pre-wrap`. Backend is the sanitisation authority; this component must only ever receive bodies written via the sanitising admin forms.

- [ ] **Step 1: Component**

```tsx
const HTML_RE = /<([a-z]+)(\s[^>]*)?>/i;

export default function RichText({ body, className = '' }: { body: string; className?: string }) {
  if (HTML_RE.test(body)) {
    return (
      <div
        className={`rich-text break-words ${className}`}
        dangerouslySetInnerHTML={{ __html: body }}
      />
    );
  }
  return <div className={`whitespace-pre-wrap break-words ${className}`}>{body}</div>;
}
```

index.css additions (Tailwind preflight strips list/link styles):

```css
@layer components {
  .rich-text ul { list-style: disc; padding-left: 1.25rem; margin: 0.5rem 0; }
  .rich-text ol { list-style: decimal; padding-left: 1.25rem; margin: 0.5rem 0; }
  .rich-text a { color: #e01e8c; text-decoration: underline; overflow-wrap: anywhere; }
  .rich-text p { margin: 0.5rem 0; }
}
```

- [ ] **Step 2: Use it** in NewsArticlePage body, HomePage featured banner summary IF summaries become rich (they do not - summaries stay plain, skip), and MessagesPage mass-message ("Announcements") bubbles only - regular chat bubbles keep plain-text rendering (rich chat is a raised decision, not built). Mobile check: long links wrap (overflow-wrap anywhere), no horizontal scroll at 360px.

- [ ] **Step 3:** Build, verify a formatted article + mass message render on desktop and 360px emulation, commit.

```bash
git add frontend/src/components/ui/RichText.tsx frontend/src/pages/NewsArticlePage.tsx frontend/src/pages/MessagesPage.tsx frontend/src/index.css
git commit -m "feat(frontend): render sanitised rich text for news articles and announcements"
```

---

### Task 26: Round summary + owner decisions writeup

**Files:**
- Create: `docs/2026-07-22-early-release-fixes-summary.md`

- [ ] **Step 1:** Write the per-item summary the round's definition of done requires: for every P1/P2/P3 item and the rich text feature - root cause, files changed, migration/config needed (migrations: messaging `edited_at`, forums `participants_notified`, sessions `created_by`; config: `django-tinymce`+`nh3` install, `collectstatic`, `sync_email_catalogue`; deploy: `docker compose up -d` after .env changes, frontend image rebuild), and how it was verified. Include the Decisions needed section with the Baillie investigation result and the link-policy recommendation.

- [ ] **Step 2:** Commit.

```bash
git add docs/2026-07-22-early-release-fixes-summary.md
git commit -m "docs: early-release testing round summary and owner decisions"
```

---

## Deployment checklist (after all tasks)

1. `pip install -r requirements.txt` in the backend image (new: django-tinymce, nh3).
2. `python manage.py migrate` (messaging, forums, sessions).
3. `python manage.py sync_email_catalogue` and `python manage.py collectstatic --noinput`.
4. Rebuild + redeploy the frontend image; `docker compose up -d` (NOT just restart - env/app changes need container recreation).
5. Re-verify on a real phone: P1-1/P1-2/P1-3 behaviours, plus the moderation queue, session booking, and goals smoke checks (do-not-regress list).
