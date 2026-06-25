# JaaS (8x8) Video Calls — Design

**Date:** 2026-06-25
**Status:** Approved (design), pending implementation plan
**Author:** Luke + Claude

## Problem

Mentoring sessions currently link to the **free public `meet.jit.si`** instance. The
public server now requires the first participant (the "moderator") to authenticate
with an external account before a call can start; everyone else sees
*"The conference has not yet started because no moderators have yet arrived… please
log-in."* A customer (Rachel) hit exactly this gate during a test call.

This is Jitsi's behaviour on the public server, not a permission on our mentoring
accounts. We are moving video calls to **JaaS (Jitsi as a Service / 8x8)** so the
backend can mint moderator tokens and remove the log-in gate entirely.

## Current behaviour (baseline)

- `MentoringSession.save()` (`backend/apps/sessions/models.py:83`) bakes a permanent
  URL into the row on first save:
  `https://meet.jit.si/SPTMentoring-{md5hash[:10]}`.
- `meeting_url` is exposed read-only via `MentoringSessionSerializer`.
- `frontend/src/pages/SessionsPage.tsx` renders a static `<a href={meeting_url}>`
  "Join Jitsi call" button, shown when the session is `confirmed`, joinable
  (within the time window), and has a `meeting_url`.

## Why a static URL no longer works

JaaS rooms reject any participant without a valid signed JWT, and the token must
encode the holder's identity and whether they are a moderator. A single permanent
URL cannot carry a per-user, time-limited token. Therefore the join URL must be
**minted on demand, per user, at the moment of joining.**

## Decisions

- **Moderator policy:** both the mentor and the scholar receive `moderator: true`.
  In a 1:1 session this means whoever joins first starts the call and nobody ever
  waits on the moderator gate. Moderator powers (mute/remove) are harmless between
  two participants.
- **Credentials:** Luke creates the 8x8 JaaS account and supplies `App ID`,
  `Key ID (kid)`, and the RS256 `private key`. The integration is built to read
  these from `.env` and works as soon as they are present.
- **Graceful fallback:** until credentials are configured, the join endpoint falls
  back to the existing `meet.jit.si` URL so the platform is never broken in the gap
  between deploy and credential entry.

## Architecture

### Token minting — `backend/apps/sessions/jaas.py` (new)

A pure, dependency-light module, independently unit-testable.

```
build_join_url(session, user) -> str
```

- Resolves a **stable room name** for the session (reuse the existing
  `SPTMentoring-{hash}` value so both participants land in the same room).
- Builds the JaaS claim set:
  - `aud`: `"jitsi"`
  - `iss`: `"chat"`
  - `sub`: the JaaS App ID
  - `room`: the specific session room name (scoped per-session, **not** the `"*"`
    wildcard — a token is only valid for that one room)
  - `nbf`: now − small skew
  - `exp`: now + ~2 hours
  - `context.user`: `{ id, name, email, moderator: "true" }`
  - `context.features`: defaults acceptable for 1:1 (no special features required)
- Signs **RS256** with the configured private key, `kid` header set.
- Returns `https://8x8.vc/{AppID}/{room}?jwt={token}`.

Helper `is_configured()` returns whether all three secrets are present.

### Settings — `backend/config/settings.py`

Read via `python-decouple` `config()` (existing pattern):

- `JAAS_APP_ID` (default `''`)
- `JAAS_KID` (default `''`)
- `JAAS_PRIVATE_KEY` (default `''`) — PEM stored single-line with escaped newlines;
  normalised back to real newlines at load.
- `JAAS_ENABLED` — derived: true when all three are non-empty.

### Endpoint — `MentoringSessionViewSet.join`

`GET /api/sessions/{id}/join/`

- **AuthZ:** caller must be the session's `mentor`, the session's `scholar`, or
  staff. Otherwise `403`.
- **State guard:** session must be `confirmed` and within the join window
  (mirror the frontend `isJoinable` rule). Otherwise `400`/`409` with a clear message.
- **Configured:** return `{ "url": build_join_url(session, request.user) }`.
- **Not configured (fallback):** return `{ "url": session.meeting_url }`
  (the existing `meet.jit.si` link).

### Model — `backend/apps/sessions/models.py`

- Keep generating the stable room identifier on save (reuse the existing hash
  logic). The stored value remains the source of the room name used by both the
  fallback URL and the JaaS room. No destructive schema change required.

### Frontend — `frontend/src/pages/SessionsPage.tsx`

- Replace the static `<a href={meeting_url}>` with a button that:
  1. calls `GET /api/sessions/{id}/join/`,
  2. opens the returned `url` in a new tab via `window.open(url, '_blank')`,
  3. shows a brief loading state and an error toast on failure.
- Visibility rules unchanged (confirmed + joinable).

### Dependencies — `backend/requirements.txt`

- Pin `PyJWT` and `cryptography` explicitly (RS256 requires the cryptography
  backend). `djangorestframework-simplejwt` already pulls PyJWT transitively, but
  we make the dependency explicit since we use it directly.

### Config docs

- `.env.example`: add `JAAS_APP_ID`, `JAAS_KID`, `JAAS_PRIVATE_KEY` with comments.
- A short step-by-step for the 8x8 console: create app, generate keypair, upload
  public key, copy App ID + Key ID + private key into `.env`, then
  `docker compose up -d backend`.

## Testing

**Unit (`jaas.py`):**
- Minted token decodes with the matching RSA public key.
- Claims correct: `aud=jitsi`, `iss=chat`, `sub=AppID`, room matches, `exp` in
  future, `nbf` not in future, `context.user.moderator` truthy.
- Returned URL has the `https://8x8.vc/{AppID}/...?jwt=` shape.
- `is_configured()` true/false per secret presence.

**API (`join` action):**
- Non-participant → `403`.
- Participant, session not confirmed / outside window → blocked with message.
- Participant, configured → returns an `8x8.vc` URL.
- Participant, not configured → returns the `meet.jit.si` fallback URL.

## Out of scope

- Embedding the Jitsi iframe in-app (we keep the open-in-new-tab UX).
- Recording, lobby, breakout rooms, or other JaaS features beyond a 1:1 call.
- Migrating historical `meeting_url` values (go-live cleardown wiped session data).

## Files touched

- `backend/apps/sessions/jaas.py` (new)
- `backend/apps/sessions/views.py` (join action)
- `backend/apps/sessions/models.py` (room name stability — minimal/none)
- `backend/config/settings.py` (JAAS_* config)
- `backend/requirements.txt` (PyJWT, cryptography)
- `backend/apps/sessions/tests/` (new tests)
- `frontend/src/pages/SessionsPage.tsx` (button → endpoint)
- `.env.example` (JAAS_* keys)
- Console setup guide (docs)
