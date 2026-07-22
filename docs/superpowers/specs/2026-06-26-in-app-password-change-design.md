# In-app password change — design

**Date:** 2026-06-26
**Status:** Approved

## Problem

Logged-in users (mentors, scholars, sponsors, admins) have no way to change their
password from inside the app. The only existing mechanism is the forgotten-password
email flow (`/forgot-password` → emailed link → `/reset-password/:uid/:token`),
which is awkward for a user who is already authenticated and simply wants to set a
new password.

## Solution

Add a self-service password change available to any authenticated user, surfaced as a
dedicated "Security" card on the profile page.

### Backend

New action on `UserViewSet` (`apps/users/views.py`), mirroring the existing `me` action:

- **Route:** `POST /api/users/me/change-password/` (`url_path='me/change-password'`)
- **Permission:** `IsAuthenticated`
- **Request body:** `{ "new_password": str, "confirm_password": str }`
- **Logic:**
  1. Reject if `new_password != confirm_password` → 400.
  2. Run `django.contrib.auth.password_validation.validate_password(new_password, user)`
     — the same validator used by `PasswordResetConfirmView`, keeping password rules
     consistent across the app.
  3. `user.set_password(new_password)` then `user.save(update_fields=['password'])`.
- **Response:** `200 {"detail": "Password updated."}` on success; `400 {"error": [...]}`
  or `{"new_password": [...]}` on validation failure; `401` if unauthenticated.

Notes / decisions:
- **No current-password check** — product decision; the form takes new + confirm only.
- **No token rotation / forced logout.** With SimpleJWT the existing access token stays
  valid after the change, so the user remains logged in. Simplest correct behaviour.
- No "password changed" notification email. Out of scope.

### Frontend

New `SecuritySection` component in `src/pages/ProfilePage.tsx`, rendered **always**
(independent of the profile edit mode), placed after the role-specific sections.

- Two password inputs (`new`, `confirm`) + a Save button + inline success/error message.
- Submits via `api.post('/users/me/change-password/', { new_password, confirm_password })`,
  following the `useState` + handler pattern already used by other forms in the file.
- Client-side guard: both fields non-empty and matching before submit; the server remains
  the source of truth for strength rules. Server field errors are surfaced inline.
- On success: clear the inputs, show a confirmation message.

## Testing

Backend tests (Django `TestCase` + DRF `APIClient`, run via `manage.py test apps.users`):

1. Authenticated user with matching valid passwords → 200, and the new password
   authenticates afterwards.
2. Mismatched `new`/`confirm` → 400, password unchanged.
3. Weak password (fails Django validators, e.g. too short) → 400, password unchanged.
4. Unauthenticated request → 401.

## Out of scope (YAGNI)

- Current-password verification.
- Token blacklist / forced re-login on change.
- Email notification of password change.
- Any admin-facing changes.
