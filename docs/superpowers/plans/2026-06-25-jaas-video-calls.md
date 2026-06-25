# JaaS (8x8) Video Calls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the public `meet.jit.si` link with JaaS (8x8) calls where the backend mints a per-user moderator JWT at join time, removing the "waiting for a moderator" log-in gate.

**Architecture:** A stable room name is kept per session. When a participant clicks Join, the frontend calls `GET /api/sessions/{id}/join/`; the backend mints a short-lived RS256-signed JaaS JWT (both mentor and scholar are moderators) and returns `https://8x8.vc/{AppID}/{room}?jwt=…`. If JaaS credentials are not configured, the endpoint falls back to the existing `meet.jit.si` URL so nothing breaks before credentials are entered.

**Tech Stack:** Django REST Framework, `python-decouple` for config, `PyJWT` + `cryptography` for RS256, React + `@tanstack/react-query` + axios (`frontend/src/utils/api.ts`).

## Global Constraints

- Config is read via `python-decouple`'s `config(...)` in `backend/config/settings.py` — match that pattern, never `os.environ` directly.
- The private key is stored in `.env` on a single line with literal `\n` escapes; it MUST be un-escaped to real newlines at load time.
- Both participants (mentor AND scholar) get `moderator: "true"` — no "mentor only" path.
- JaaS join URL shape is exactly `https://8x8.vc/{AppID}/{room}?jwt={token}`.
- JWT is RS256 with a `kid` header; JaaS claim set: `aud="jitsi"`, `iss="chat"`, `sub={AppID}`, `room={room_name}` (specific room, never `"*"`).
- Token lifetime ~2 hours; `nbf` backdated ~10s for clock skew.
- Keep the open-in-new-tab UX (no in-app iframe).
- Backend tests use `pytest`-style modules under `backend/apps/sessions/tests/` mirroring `backend/apps/moderation/tests/`. Run with the project's test runner (`python manage.py test apps.sessions` from `backend/`, or `pytest` if configured).

---

### Task 1: Dependencies + JaaS settings + .env.example

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/config/settings.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: Django settings `JAAS_APP_ID: str`, `JAAS_KID: str`, `JAAS_PRIVATE_KEY: str` (real newlines), `JAAS_ENABLED: bool`. Later tasks read these via `from django.conf import settings`.

- [ ] **Step 1: Pin the crypto libraries**

In `backend/requirements.txt`, add (PyJWT is currently only transitive via `djangorestframework-simplejwt`; make it explicit, and `cryptography` is required for RS256):

```
PyJWT==2.9.0
cryptography==43.0.1
```

- [ ] **Step 2: Add JaaS config to settings**

Append to `backend/config/settings.py` (after the existing `config(...)` blocks, e.g. near the REDIS/email config):

```python
# --- JaaS (8x8) video calls ---
JAAS_APP_ID = config('JAAS_APP_ID', default='')
JAAS_KID = config('JAAS_KID', default='')
# Private key is stored single-line in .env with literal \n; restore real newlines.
JAAS_PRIVATE_KEY = config('JAAS_PRIVATE_KEY', default='').replace('\\n', '\n')
JAAS_ENABLED = bool(JAAS_APP_ID and JAAS_KID and JAAS_PRIVATE_KEY)
```

- [ ] **Step 3: Document the env vars**

Add to `.env.example`:

```
# --- JaaS (8x8) video calls ---
# Leave blank to fall back to the public meet.jit.si server.
# Obtain these from the 8x8 JaaS console (see docs/jaas-setup.md).
JAAS_APP_ID=
JAAS_KID=
# Paste the RS256 private key as a single line with \n between each line, e.g.
# JAAS_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----
JAAS_PRIVATE_KEY=
```

- [ ] **Step 4: Verify settings import cleanly**

Run from `backend/`:

```bash
python manage.py check
```

Expected: `System check identified no issues` (and no import error). With no JaaS env set, `JAAS_ENABLED` is `False`.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/config/settings.py .env.example
git commit -m "feat(sessions): add JaaS config plumbing and pin crypto deps"
```

---

### Task 2: Model helpers — `room_name` and `is_joinable`

**Files:**
- Modify: `backend/apps/sessions/models.py`
- Create: `backend/apps/sessions/tests/__init__.py` (if missing)
- Test: `backend/apps/sessions/tests/test_session_model.py`

**Interfaces:**
- Produces: `MentoringSession.room_name -> str` (stable JaaS/Jitsi room id) and `MentoringSession.is_joinable -> bool`. Task 4 consumes both.

- [ ] **Step 1: Write the failing tests**

Create `backend/apps/sessions/tests/test_session_model.py`:

```python
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.users.models import User
from apps.sessions.models import MentoringSession


class SessionModelHelpersTest(TestCase):
    def setUp(self):
        self.mentor = User.objects.create_user(
            email='m@example.com', password='x', first_name='Mary', last_name='Mentor', role='mentor')
        self.scholar = User.objects.create_user(
            email='s@example.com', password='x', first_name='Sam', last_name='Scholar', role='scholar')

    def _session(self, start, end, status=MentoringSession.Status.CONFIRMED):
        return MentoringSession.objects.create(
            mentor=self.mentor, scholar=self.scholar,
            start_time=start, end_time=end, status=status)

    def test_room_name_is_stable_and_prefixed(self):
        now = timezone.now()
        s = self._session(now, now + timedelta(hours=1))
        self.assertTrue(s.room_name.startswith('SPTMentoring-'))
        # Stable across reloads from the DB.
        self.assertEqual(s.room_name, MentoringSession.objects.get(pk=s.pk).room_name)

    def test_is_joinable_true_within_window(self):
        now = timezone.now()
        s = self._session(now - timedelta(minutes=1), now + timedelta(minutes=59))
        self.assertTrue(s.is_joinable)

    def test_is_joinable_false_when_too_early(self):
        now = timezone.now()
        s = self._session(now + timedelta(hours=1), now + timedelta(hours=2))
        self.assertFalse(s.is_joinable)

    def test_is_joinable_false_when_not_confirmed(self):
        now = timezone.now()
        s = self._session(now - timedelta(minutes=1), now + timedelta(minutes=59),
                          status=MentoringSession.Status.PENDING)
        self.assertFalse(s.is_joinable)
```

Create `backend/apps/sessions/tests/__init__.py` (empty) if it does not exist.

- [ ] **Step 2: Run tests to verify they fail**

Run from `backend/`:

```bash
python manage.py test apps.sessions.tests.test_session_model -v 2
```

Expected: FAIL — `AttributeError: 'MentoringSession' object has no attribute 'room_name'` (and `is_joinable`).

- [ ] **Step 3: Add the properties**

In `backend/apps/sessions/models.py`, add `from datetime import timedelta` to the imports, then add to `MentoringSession` (next to the existing `is_upcoming` property):

```python
    @property
    def room_name(self):
        """Stable room id shared by both participants (JaaS room or Jitsi path)."""
        if self.meeting_url:
            return self.meeting_url.rstrip('/').rsplit('/', 1)[-1]
        token = hashlib.md5(
            f"spt-{self.mentor_id}-{self.scholar_id}-{self.start_time}".encode()
        ).hexdigest()[:10]
        return f"SPTMentoring-{token}"

    @property
    def is_joinable(self):
        """Confirmed and within the join window (5 min before start until end)."""
        now = timezone.now()
        return (
            self.status == self.Status.CONFIRMED
            and self.start_time - timedelta(minutes=5) <= now <= self.end_time
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run from `backend/`:

```bash
python manage.py test apps.sessions.tests.test_session_model -v 2
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/sessions/models.py backend/apps/sessions/tests/__init__.py backend/apps/sessions/tests/test_session_model.py
git commit -m "feat(sessions): add room_name and is_joinable helpers"
```

---

### Task 3: JaaS token-minting module

**Files:**
- Create: `backend/apps/sessions/jaas.py`
- Test: `backend/apps/sessions/tests/test_jaas.py`

**Interfaces:**
- Consumes: `settings.JAAS_APP_ID/JAAS_KID/JAAS_PRIVATE_KEY/JAAS_ENABLED` (Task 1); `session.room_name` (Task 2); `user.id/full_name/email`.
- Produces:
  - `is_configured() -> bool`
  - `build_join_url(session, user) -> str` returning `https://8x8.vc/{AppID}/{room}?jwt={token}`.

- [ ] **Step 1: Write the failing tests**

Create `backend/apps/sessions/tests/test_jaas.py`:

```python
from datetime import timedelta
from urllib.parse import urlparse, parse_qs

import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.users.models import User
from apps.sessions.models import MentoringSession
from apps.sessions import jaas


def _make_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


PRIVATE_PEM, PUBLIC_PEM = _make_keypair()

JAAS_SETTINGS = dict(
    JAAS_APP_ID='vpaas-magic-cookie-test',
    JAAS_KID='vpaas-magic-cookie-test/abc123',
    JAAS_PRIVATE_KEY=PRIVATE_PEM,
    JAAS_ENABLED=True,
)


class JaaSTest(TestCase):
    def setUp(self):
        self.mentor = User.objects.create_user(
            email='m@example.com', password='x', first_name='Mary', last_name='Mentor', role='mentor')
        self.scholar = User.objects.create_user(
            email='s@example.com', password='x', first_name='Sam', last_name='Scholar', role='scholar')
        now = timezone.now()
        self.session = MentoringSession.objects.create(
            mentor=self.mentor, scholar=self.scholar,
            start_time=now, end_time=now + timedelta(hours=1),
            status=MentoringSession.Status.CONFIRMED)

    @override_settings(JAAS_APP_ID='', JAAS_KID='', JAAS_PRIVATE_KEY='', JAAS_ENABLED=False)
    def test_is_configured_false_when_blank(self):
        self.assertFalse(jaas.is_configured())

    @override_settings(**JAAS_SETTINGS)
    def test_is_configured_true_when_set(self):
        self.assertTrue(jaas.is_configured())

    @override_settings(**JAAS_SETTINGS)
    def test_build_join_url_shape(self):
        url = jaas.build_join_url(self.session, self.mentor)
        parsed = urlparse(url)
        self.assertEqual(parsed.scheme, 'https')
        self.assertEqual(parsed.netloc, '8x8.vc')
        self.assertTrue(parsed.path.startswith('/vpaas-magic-cookie-test/'))
        self.assertIn('jwt', parse_qs(parsed.query))

    @override_settings(**JAAS_SETTINGS)
    def test_token_claims_decode_with_public_key(self):
        url = jaas.build_join_url(self.session, self.mentor)
        token = parse_qs(urlparse(url).query)['jwt'][0]
        claims = pyjwt.decode(token, PUBLIC_PEM, algorithms=['RS256'], audience='jitsi')
        self.assertEqual(claims['iss'], 'chat')
        self.assertEqual(claims['sub'], 'vpaas-magic-cookie-test')
        self.assertEqual(claims['room'], self.session.room_name)
        self.assertEqual(claims['context']['user']['moderator'], 'true')
        self.assertEqual(claims['context']['user']['email'], 'm@example.com')

    @override_settings(**JAAS_SETTINGS)
    def test_token_kid_header_set(self):
        url = jaas.build_join_url(self.session, self.scholar)
        token = parse_qs(urlparse(url).query)['jwt'][0]
        header = pyjwt.get_unverified_header(token)
        self.assertEqual(header['kid'], 'vpaas-magic-cookie-test/abc123')
        self.assertEqual(header['alg'], 'RS256')
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `backend/`:

```bash
python manage.py test apps.sessions.tests.test_jaas -v 2
```

Expected: FAIL — `ModuleNotFoundError: No module named 'apps.sessions.jaas'`.

- [ ] **Step 3: Implement the module**

Create `backend/apps/sessions/jaas.py`:

```python
"""JaaS (8x8) join-URL minting.

Builds a short-lived RS256 JWT per participant so the backend can grant
moderator rights without the public meet.jit.si log-in gate.
"""
from datetime import timedelta

import jwt as pyjwt
from django.conf import settings
from django.utils import timezone

JAAS_BASE = 'https://8x8.vc'
TOKEN_TTL = timedelta(hours=2)
CLOCK_SKEW = timedelta(seconds=10)


def is_configured():
    """True when all JaaS secrets are present."""
    return bool(settings.JAAS_ENABLED)


def build_join_url(session, user):
    """Return a JaaS join URL carrying a moderator JWT for `user`."""
    now = timezone.now()
    room = session.room_name
    payload = {
        'aud': 'jitsi',
        'iss': 'chat',
        'sub': settings.JAAS_APP_ID,
        'room': room,
        'nbf': int((now - CLOCK_SKEW).timestamp()),
        'exp': int((now + TOKEN_TTL).timestamp()),
        'context': {
            'user': {
                'id': str(user.id),
                'name': user.full_name,
                'email': user.email,
                'moderator': 'true',
            },
            'features': {
                'recording': 'false',
                'livestreaming': 'false',
                'transcription': 'false',
                'outbound-call': 'false',
            },
        },
    }
    token = pyjwt.encode(
        payload,
        settings.JAAS_PRIVATE_KEY,
        algorithm='RS256',
        headers={'kid': settings.JAAS_KID, 'typ': 'JWT'},
    )
    return f'{JAAS_BASE}/{settings.JAAS_APP_ID}/{room}?jwt={token}'
```

- [ ] **Step 4: Run tests to verify they pass**

Run from `backend/`:

```bash
python manage.py test apps.sessions.tests.test_jaas -v 2
```

Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/sessions/jaas.py backend/apps/sessions/tests/test_jaas.py
git commit -m "feat(sessions): add JaaS JWT minting module"
```

---

### Task 4: `join` API endpoint

**Files:**
- Modify: `backend/apps/sessions/views.py`
- Test: `backend/apps/sessions/tests/test_join_endpoint.py`

**Interfaces:**
- Consumes: `jaas.is_configured()`, `jaas.build_join_url(session, user)` (Task 3); `session.is_joinable` (Task 2); `session.meeting_url` (existing).
- Produces: `GET /api/sessions/sessions/{id}/join/` → `{"url": str}`. (Route is `/sessions/sessions/...` because the DRF router registers the `sessions` viewset under the app's `sessions/` include.)

- [ ] **Step 1: Write the failing tests**

Create `backend/apps/sessions/tests/test_join_endpoint.py`:

```python
from datetime import timedelta
from urllib.parse import urlparse

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import User
from apps.sessions.models import MentoringSession
from apps.sessions.tests.test_jaas import JAAS_SETTINGS


class JoinEndpointTest(TestCase):
    def setUp(self):
        self.mentor = User.objects.create_user(
            email='m@example.com', password='x', first_name='Mary', last_name='Mentor', role='mentor')
        self.scholar = User.objects.create_user(
            email='s@example.com', password='x', first_name='Sam', last_name='Scholar', role='scholar')
        self.outsider = User.objects.create_user(
            email='o@example.com', password='x', first_name='Otto', last_name='Outsider', role='mentor')
        now = timezone.now()
        self.session = MentoringSession.objects.create(
            mentor=self.mentor, scholar=self.scholar,
            start_time=now - timedelta(minutes=1), end_time=now + timedelta(minutes=59),
            status=MentoringSession.Status.CONFIRMED)
        self.url = f'/api/sessions/sessions/{self.session.pk}/join/'

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_outsider_cannot_see_session(self):
        # get_queryset scopes non-staff to their own sessions -> 404.
        resp = self._client(self.outsider).get(self.url)
        self.assertEqual(resp.status_code, 404)

    @override_settings(**JAAS_SETTINGS)
    def test_participant_gets_jaas_url(self):
        resp = self._client(self.scholar).get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(urlparse(resp.data['url']).netloc, '8x8.vc')

    @override_settings(JAAS_APP_ID='', JAAS_KID='', JAAS_PRIVATE_KEY='', JAAS_ENABLED=False)
    def test_falls_back_to_jitsi_when_unconfigured(self):
        resp = self._client(self.mentor).get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['url'], self.session.meeting_url)
        self.assertIn('meet.jit.si', resp.data['url'])

    @override_settings(**JAAS_SETTINGS)
    def test_not_joinable_is_rejected(self):
        self.session.start_time = timezone.now() + timedelta(hours=2)
        self.session.end_time = timezone.now() + timedelta(hours=3)
        self.session.save(update_fields=['start_time', 'end_time'])
        resp = self._client(self.mentor).get(self.url)
        self.assertEqual(resp.status_code, 409)
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `backend/`:

```bash
python manage.py test apps.sessions.tests.test_join_endpoint -v 2
```

Expected: FAIL — the `join` route does not exist yet (404 for the configured/fallback cases, assertion failures).

- [ ] **Step 3: Add the `join` action**

In `backend/apps/sessions/views.py`, add this action to `MentoringSessionViewSet` (e.g. after `complete`):

```python
    @action(detail=True, methods=['get'])
    def join(self, request, pk=None):
        session = self.get_object()
        user = request.user
        if user not in (session.mentor, session.scholar) and not (user.is_staff or user.role == 'admin'):
            return Response({'error': 'Not authorised.'}, status=status.HTTP_403_FORBIDDEN)
        if not session.is_joinable:
            return Response(
                {'error': 'This session is not open to join right now.'},
                status=status.HTTP_409_CONFLICT,
            )
        from .jaas import build_join_url, is_configured
        url = build_join_url(session, user) if is_configured() else session.meeting_url
        return Response({'url': url})
```

- [ ] **Step 4: Run tests to verify they pass**

Run from `backend/`:

```bash
python manage.py test apps.sessions.tests.test_join_endpoint -v 2
```

Expected: PASS (4 tests).

- [ ] **Step 5: Run the full sessions suite**

```bash
python manage.py test apps.sessions -v 2
```

Expected: all sessions tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/sessions/views.py backend/apps/sessions/tests/test_join_endpoint.py
git commit -m "feat(sessions): add JaaS join endpoint with meet.jit.si fallback"
```

---

### Task 5: Frontend Join button → endpoint

**Files:**
- Modify: `frontend/src/pages/SessionsPage.tsx`

**Interfaces:**
- Consumes: `GET /sessions/sessions/{id}/join/` → `{ url: string }` via `api` (`frontend/src/utils/api.ts`, axios instance; base URL already includes `/api`).

- [ ] **Step 1: Replace the static anchor with an endpoint-driven button**

In `frontend/src/pages/SessionsPage.tsx`, find the join block (around line 206):

```tsx
            {session.status === 'confirmed' && isJoinable && session.meeting_url && (
              <a href={session.meeting_url} target="_blank" rel="noopener noreferrer"
                className="text-xs font-semibold bg-gradient-brand text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.723v6.554a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Join Jitsi call
              </a>
            )}
```

Replace it with a button that fetches the minted URL and opens it:

```tsx
            {session.status === 'confirmed' && isJoinable && (
              <button
                type="button"
                disabled={joining}
                onClick={async () => {
                  setJoining(true);
                  try {
                    const { data } = await api.get(`/sessions/sessions/${session.id}/join/`);
                    window.open(data.url, '_blank', 'noopener,noreferrer');
                  } catch {
                    alert('Could not start the video call. Please try again in a moment.');
                  } finally {
                    setJoining(false);
                  }
                }}
                className="text-xs font-semibold bg-gradient-brand text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity flex items-center gap-1 disabled:opacity-60">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.723v6.554a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                {joining ? 'Starting…' : 'Join video call'}
              </button>
            )}
```

- [ ] **Step 2: Add the `joining` state**

This join block lives inside the per-session card component (the same component that defines `isJoinable` at line 176). Add a state hook near the top of that component, alongside the other hooks:

```tsx
  const [joining, setJoining] = useState(false);
```

Ensure `useState` is imported at the top of the file (it is used elsewhere in this file; if the join block's component does not already import it, add `useState` to the existing `import { ... } from 'react';`).

- [ ] **Step 3: Build the frontend to verify it compiles**

Run from `frontend/`:

```bash
npm run build
```

Expected: build succeeds with no TypeScript errors. (`session.meeting_url` is no longer referenced in the join block; the `meeting_url` field on the type can remain.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SessionsPage.tsx
git commit -m "feat(sessions): join button mints call URL via API"
```

---

### Task 6: 8x8 console setup guide

**Files:**
- Create: `docs/jaas-setup.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Write the setup guide**

Create `docs/jaas-setup.md`:

```markdown
# JaaS (8x8) setup for video calls

The mentoring platform mints its own moderator tokens for video calls. To enable
this you need a free 8x8 JaaS account and three secrets in `.env`.

## 1. Create the JaaS app
1. Go to https://jaas.8x8.vc and sign up / log in.
2. Create an application. Note the **App ID** — it looks like
   `vpaas-magic-cookie-xxxxxxxxxxxx`.

## 2. Generate an API key
1. In the JaaS console, open **API Keys** and add a new key pair.
2. Download/keep the **private key** (PEM). The console keeps the public half.
3. Note the **Key ID (kid)** shown for the key — usually
   `vpaas-magic-cookie-xxxx/yyyyyy`.

## 3. Put the secrets in `.env`
- `JAAS_APP_ID` = the App ID from step 1.
- `JAAS_KID` = the Key ID from step 2.
- `JAAS_PRIVATE_KEY` = the private key PEM on **one line** with `\n` between each
  line. To convert a key file to a single line:

  ```bash
  awk 'NF {printf "%s\\n", $0}' your-key.pk > one-line.txt
  ```

  Paste the result after `JAAS_PRIVATE_KEY=`.

## 4. Apply
```bash
docker compose up -d backend
```

`docker compose restart` does NOT pick up `.env` changes — use `up -d`.

## Verifying
- With the three vars set, the "Join video call" button opens an `8x8.vc` URL and
  the call starts immediately with no log-in gate.
- If the vars are blank, the platform falls back to the public `meet.jit.si`
  server (the old behaviour, including its moderator gate).
```

- [ ] **Step 2: Commit**

```bash
git add docs/jaas-setup.md
git commit -m "docs(sessions): add 8x8 JaaS console setup guide"
```

---

## Notes for the implementer

- Run backend tests from the `backend/` directory. If the project uses `pytest`, `pytest apps/sessions/` also works; otherwise use `python manage.py test apps.sessions`.
- The DRF route is `/api/sessions/sessions/{id}/join/` — the doubled `sessions` is correct (app include `sessions/` + router prefix `sessions`), matching the existing `/sessions/sessions/{id}/{action}/` calls in `SessionsPage.tsx:688`.
- Do not remove the `meeting_url` model field — it is the fallback URL and the source of the stable `room_name`.
