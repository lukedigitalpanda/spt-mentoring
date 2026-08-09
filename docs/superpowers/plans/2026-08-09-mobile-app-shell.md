# Mobile App Shell + Connectivity + Branding — Implementation Plan (Plan 1 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the existing React frontend as installable, branded iOS + Android apps (via Capacitor) that run the whole platform against the production backend, including live WebSocket messaging and JaaS video.

**Architecture:** A new `mobile/` Capacitor project bundles the compiled `frontend/dist` and adds native iOS/Android shells + plugins (splash, status bar, app). The web UI stays the single source of truth. API/WebSocket calls go to the production Django backend over HTTPS. The only shared-frontend code change makes the API and WebSocket base URLs configurable so they work from the bundled `localhost` origin instead of a same-origin proxy.

**Tech Stack:** Capacitor 6, existing Vite/React 18 frontend, `@capacitor/assets` for icon/splash generation, Django + Channels backend (config-only change).

## Global Constraints

- App ID (both platforms): `org.spt.mentoring` — copied verbatim from the abandoned scaffold's `app.json`; keep it stable (changing it later orphans store listings).
- App display name: `SPT Mentoring`.
- Brand colors: primary purple `#6b21a8`, accent `#9333ea`.
- Production backend origin: `https://mentoring.smallpeice.online` (API base `https://mentoring.smallpeice.online/api`).
- Capacitor bundled web origin: `https://localhost` (Android, `androidScheme: 'https'`) and `capacitor://localhost` (iOS default). Both must be accepted by backend CORS.
- The shared frontend change MUST remain correct for the existing website build (where no app env vars are set) — default behaviour is unchanged when `VITE_WS_URL` is absent.
- iOS compile/run happens on Luke's Mac (Xcode). Android may build here (if Android SDK present) or on the Mac.
- Do NOT modify the core Django REST API. Backend change in this plan is CORS config only.

---

### Task 1: Remove the abandoned Expo scaffold and baseline-commit

**Files:**
- Delete: everything under `mobile/` (abandoned Expo/React Native scaffold — never committed, internally inconsistent).

**Interfaces:**
- Consumes: nothing.
- Produces: a clean empty `mobile/` for the Capacitor project.

- [ ] **Step 1: Confirm the scaffold is untracked (safe to delete)**

Run: `git -C /opt/spt-mentoring status --porcelain mobile/`
Expected: no tracked/staged entries for `mobile/` (it was never committed). If anything is tracked, stop and review before deleting.

- [ ] **Step 2: Remove the scaffold**

```bash
rm -rf /opt/spt-mentoring/mobile
mkdir -p /opt/spt-mentoring/mobile
```

- [ ] **Step 3: Verify frontend still builds (baseline)**

Run: `cd /opt/spt-mentoring/frontend && npm run build`
Expected: build succeeds, `frontend/dist/index.html` exists.

Run: `ls /opt/spt-mentoring/frontend/dist/index.html`
Expected: file listed.

- [ ] **Step 4: Commit**

```bash
cd /opt/spt-mentoring
git add -A mobile
git commit -m "chore(mobile): clear abandoned Expo scaffold ahead of Capacitor"
```

---

### Task 2: Make frontend API + WebSocket base URLs configurable for the bundled origin

**Files:**
- Modify: `frontend/src/pages/MessagesPage.tsx:230-234` (WebSocket URL construction)
- Create: `frontend/src/utils/wsBase.ts` (WebSocket base-URL helper)
- Reference (already configurable, no change): `frontend/src/utils/api.ts` uses `import.meta.env.VITE_API_URL`.

**Interfaces:**
- Produces: `wsBase(): string` — returns the WebSocket origin (e.g. `wss://mentoring.smallpeice.online`) with NO trailing slash and NO path. Defaults to the current page origin when `VITE_WS_URL` is unset, preserving website behaviour.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/utils/wsBase.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from 'vitest';
import { wsBase } from './wsBase';

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

describe('wsBase', () => {
  it('uses VITE_WS_URL when set (bundled app)', () => {
    vi.stubEnv('VITE_WS_URL', 'wss://mentoring.smallpeice.online');
    expect(wsBase()).toBe('wss://mentoring.smallpeice.online');
  });

  it('falls back to the page origin on https (website)', () => {
    vi.stubEnv('VITE_WS_URL', '');
    vi.stubGlobal('location', { protocol: 'https:', host: 'mentoring.smallpeice.online' });
    expect(wsBase()).toBe('wss://mentoring.smallpeice.online');
  });

  it('falls back to ws:// on http (local dev)', () => {
    vi.stubEnv('VITE_WS_URL', '');
    vi.stubGlobal('location', { protocol: 'http:', host: 'localhost:3000' });
    expect(wsBase()).toBe('ws://localhost:3000');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /opt/spt-mentoring/frontend && npx vitest run src/utils/wsBase.test.ts`
Expected: FAIL — cannot find module `./wsBase`.
(If vitest is not installed, add it: `npm i -D vitest`, and add `"test": "vitest"` to `frontend/package.json` scripts. This is the first test in the frontend, so this setup is expected.)

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/utils/wsBase.ts`:

```ts
// Returns the WebSocket origin (scheme + host, no trailing slash, no path).
// In the bundled mobile app the page origin is `localhost`, so the real
// backend must be supplied via VITE_WS_URL at build time. On the website
// VITE_WS_URL is unset and we derive it from the current page origin.
export function wsBase(): string {
  const configured = import.meta.env.VITE_WS_URL;
  if (configured) return configured;
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /opt/spt-mentoring/frontend && npx vitest run src/utils/wsBase.test.ts`
Expected: PASS (3 passed).

- [ ] **Step 5: Use the helper in MessagesPage**

In `frontend/src/pages/MessagesPage.tsx`, add the import near the other imports:

```ts
import { wsBase } from '../utils/wsBase';
```

Replace lines 233-234:

```ts
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/chat/${selectedConv}/?token=${token}`);
```

with:

```ts
    const ws = new WebSocket(`${wsBase()}/ws/chat/${selectedConv}/?token=${token}`);
```

- [ ] **Step 6: Verify the website build is unchanged**

Run: `cd /opt/spt-mentoring/frontend && npm run build`
Expected: `tsc` + vite build succeed with no type errors.

- [ ] **Step 7: Commit**

```bash
cd /opt/spt-mentoring
git add frontend/src/utils/wsBase.ts frontend/src/utils/wsBase.test.ts frontend/src/pages/MessagesPage.tsx frontend/package.json
git commit -m "feat(frontend): make WebSocket base URL configurable via VITE_WS_URL"
```

---

### Task 3: Scaffold the Capacitor project bundling frontend/dist

**Files:**
- Create: `mobile/package.json`, `mobile/capacitor.config.ts`
- Create (generated): `mobile/node_modules/` (gitignored)

**Interfaces:**
- Consumes: `frontend/dist` (built web assets).
- Produces: a Capacitor project whose `webDir` is `../frontend/dist`, appId `org.spt.mentoring`, ready for `npx cap add`.

- [ ] **Step 1: Init the Capacitor project**

```bash
cd /opt/spt-mentoring/mobile
npm init -y
npm i @capacitor/core@6 @capacitor/cli@6 @capacitor/android@6 @capacitor/ios@6 \
      @capacitor/splash-screen@6 @capacitor/status-bar@6 @capacitor/app@6
npx cap init "SPT Mentoring" org.spt.mentoring --web-dir "../frontend/dist"
```

- [ ] **Step 2: Configure `mobile/capacitor.config.ts`**

Replace the generated file with:

```ts
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'org.spt.mentoring',
  appName: 'SPT Mentoring',
  webDir: '../frontend/dist',
  server: {
    androidScheme: 'https', // bundled origin becomes https://localhost on Android
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1200,
      backgroundColor: '#6b21a8',
      showSpinner: false,
    },
  },
};

export default config;
```

- [ ] **Step 3: Add a `.gitignore` for the mobile project**

Create `mobile/.gitignore`:

```
node_modules/
ios/App/Pods/
ios/App/build/
android/.gradle/
android/app/build/
android/build/
*.log
```

- [ ] **Step 4: Verify Capacitor sees the web assets**

Run: `cd /opt/spt-mentoring/frontend && npm run build && cd ../mobile && npx cap copy`
Expected: `npx cap copy` reports copying web assets from `../frontend/dist` with no "webDir does not exist" error.
(No platforms added yet, so `copy` may warn there are no native platforms — that is fine at this step.)

- [ ] **Step 5: Commit**

```bash
cd /opt/spt-mentoring
git add mobile/package.json mobile/package-lock.json mobile/capacitor.config.ts mobile/.gitignore
git commit -m "feat(mobile): scaffold Capacitor project bundling frontend/dist"
```

---

### Task 4: Accept the app origin in backend CORS

**Files:**
- Modify: production `.env` `CORS_ALLOWED_ORIGINS` (deployment step — the setting is already config-driven at `backend/config/settings.py:143`).

**Interfaces:**
- Consumes: nothing.
- Produces: backend responds with `Access-Control-Allow-Origin` for the app origins, so webview `fetch`/`axios` calls succeed.

- [ ] **Step 1: Add the app origins to the production `.env`**

In `/opt/spt-mentoring/.env`, append the two Capacitor origins to the existing `CORS_ALLOWED_ORIGINS` value (comma-separated, keep existing entries):

```
CORS_ALLOWED_ORIGINS=<existing values>,https://localhost,capacitor://localhost
```

- [ ] **Step 2: Restart the backend so the new env is read**

Per project infra: env changes need a container recreate, not just restart.

```bash
cd /opt/spt-mentoring && docker compose up -d backend
```

- [ ] **Step 3: Verify CORS with a preflight-style request**

Run:

```bash
curl -s -I -H "Origin: https://localhost" -H "Access-Control-Request-Method: GET" \
  -X OPTIONS https://mentoring.smallpeice.online/api/ | grep -i "access-control-allow-origin"
```

Expected: header `access-control-allow-origin: https://localhost` present.

- [ ] **Step 4: Commit (documentation of the required env)**

Add a note to `.env.example` documenting the required app origins, then commit that (never commit the real `.env`):

```bash
cd /opt/spt-mentoring
git add .env.example
git commit -m "docs(env): document Capacitor app origins required in CORS_ALLOWED_ORIGINS"
```

---

### Task 5: Generate branded app icon + splash

**Files:**
- Create: `mobile/assets/icon.png` (1024×1024, logo on white or transparent), `mobile/assets/splash.png` (2732×2732, logo centered on `#6b21a8`).
- Create (generated): `mobile/android/.../res/...` and `mobile/ios/.../Assets.xcassets/...` icon/splash sets (produced in Task 6/7 after platforms are added).

**Interfaces:**
- Consumes: the SPT logo source (high-res/vector if Luke provides it; otherwise `frontend/public/sptlogo.webp` upscaled).
- Produces: `@capacitor/assets`-ready source images.

- [ ] **Step 1: Place the source logo**

If Luke provided a high-res/vector logo, export it to a 1024×1024 PNG at `mobile/assets/icon.png`. Otherwise convert the existing logo:

```bash
cd /opt/spt-mentoring
# Fallback from the webp if no high-res source is available:
# (ImageMagick) pad to a square 1024 canvas, transparent background
convert frontend/public/sptlogo.webp -resize 820x820 -gravity center -background none -extent 1024x1024 mobile/assets/icon.png
```

- [ ] **Step 2: Create the splash source (logo on brand purple)**

```bash
cd /opt/spt-mentoring
convert frontend/public/sptlogo.webp -resize 1000x1000 -gravity center -background "#6b21a8" -extent 2732x2732 mobile/assets/splash.png
```

- [ ] **Step 3: Verify the source images exist and are the right size**

Run: `identify mobile/assets/icon.png mobile/assets/splash.png`
Expected: `1024x1024` for icon, `2732x2732` for splash.

- [ ] **Step 4: Commit the source assets**

```bash
cd /opt/spt-mentoring
git add mobile/assets/icon.png mobile/assets/splash.png
git commit -m "feat(mobile): add branded icon + splash source assets"
```

Note: the per-platform icon/splash sets are generated by `npx @capacitor/assets generate` in Tasks 6 and 7, after the native platforms exist.

---

### Task 6: Add the Android platform and smoke-test the full app

**Files:**
- Create (generated): `mobile/android/` (native Android project).

**Interfaces:**
- Consumes: `frontend/dist` built with app env; Capacitor config; icon/splash sources.
- Produces: a runnable Android app talking to production.

- [ ] **Step 1: Build the frontend with app env vars**

Create `frontend/.env.mobile`:

```
VITE_API_URL=https://mentoring.smallpeice.online/api
VITE_WS_URL=wss://mentoring.smallpeice.online
```

Build using it:

```bash
cd /opt/spt-mentoring/frontend
npx vite build --mode mobile
```

(Vite reads `.env.mobile` for `--mode mobile`. Confirm `dist/` regenerated.)

- [ ] **Step 2: Add the Android platform and sync**

```bash
cd /opt/spt-mentoring/mobile
npx cap add android
npx @capacitor/assets generate --android
npx cap sync android
```

- [ ] **Step 3: Run on an emulator or device (Mac or Linux with Android SDK)**

```bash
cd /opt/spt-mentoring/mobile
npx cap run android
```

Expected: app launches, shows the purple splash then the SPT login screen.

- [ ] **Step 4: Manual smoke checklist (record pass/fail for each)**

- [ ] Login with a real account succeeds (proves API base URL + CORS).
- [ ] Open Messages, select a conversation, send a message and see it appear live (proves WebSocket base URL fix).
- [ ] Open Forums — threads load.
- [ ] Open Profile — data + avatar/media load over HTTPS (proves media URLs).
- [ ] App icon on the home screen is the SPT logo; splash is purple.

- [ ] **Step 5: Commit the Android project**

```bash
cd /opt/spt-mentoring
git add mobile/android frontend/.env.mobile
git commit -m "feat(mobile): add Android platform, branded assets, prod connectivity"
```

---

### Task 7: Add the iOS platform, camera/mic permissions, and verify JaaS video (early-risk milestone)

**Files:**
- Create (generated): `mobile/ios/` (native Xcode project).
- Modify: `mobile/ios/App/App/Info.plist` (camera + microphone usage descriptions).

**Interfaces:**
- Consumes: same built `frontend/dist`, Capacitor config, icon/splash.
- Produces: a runnable iOS app; a verified answer to "does JaaS video work in-app?".

- [ ] **Step 1: Add the iOS platform and generate assets (on the Mac)**

```bash
cd /opt/spt-mentoring/mobile
npx cap add ios
npx @capacitor/assets generate --ios
npx cap sync ios
```

- [ ] **Step 2: Add camera + microphone usage strings to `Info.plist`**

In `mobile/ios/App/App/Info.plist`, add inside the top-level `<dict>`:

```xml
<key>NSCameraUsageDescription</key>
<string>SPT Mentoring uses your camera for video mentoring sessions.</string>
<key>NSMicrophoneUsageDescription</key>
<string>SPT Mentoring uses your microphone for video mentoring sessions.</string>
```

- [ ] **Step 3: Open in Xcode, set the signing team, run on a real device**

```bash
cd /opt/spt-mentoring/mobile
npx cap open ios
```

In Xcode: select the `App` target → Signing & Capabilities → set Team to the SPT Apple Developer account. Run on a connected iPhone.
Expected: app launches to the SPT login screen.

- [ ] **Step 4: VIDEO VERIFICATION MILESTONE — start a JaaS call in-app**

- [ ] Log in, start/join a video session.
- [ ] iOS prompts for camera + microphone permission → grant.
- [ ] Confirm two-way audio/video works.

**Decision gate:**
- If video works → it ships in v1. Record the result.
- If video fails in the webview → implement the v1 fallback: open the JaaS call URL in the system browser (`@capacitor/browser`) instead of in-app. Log this as a follow-up for a proper in-app fix. Do NOT let this block the rest of v1.

- [ ] **Step 5: Repeat the Task 6 Step-4 smoke checklist on iOS**

Login, live messaging, forums, profile/media — all must pass on iOS too.

- [ ] **Step 6: Commit the iOS project**

```bash
cd /opt/spt-mentoring
git add mobile/ios
git commit -m "feat(mobile): add iOS platform, camera/mic permissions, video verified"
```

---

### Task 8: Document the build-and-sync workflow

**Files:**
- Create: `mobile/README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: a repeatable "ship a web change into the apps" runbook.

- [ ] **Step 1: Write the runbook**

Create `mobile/README.md`:

```markdown
# SPT Mentoring — Mobile Apps (Capacitor)

Wraps the `frontend/` React app as iOS + Android apps. The web UI is the single
source of truth; this project only adds the native shell.

## Ship a web change into the apps
1. `cd ../frontend && npx vite build --mode mobile`   # builds with prod API/WS URLs
2. `cd ../mobile && npx cap sync`                      # copies build + updates native
3. Android: `npx cap run android`  ·  iOS: `npx cap open ios` then run/archive in Xcode

## Config
- App ID: `org.spt.mentoring` · Name: `SPT Mentoring`
- Backend: https://mentoring.smallpeice.online (set in `frontend/.env.mobile`)
- Backend CORS must allow `https://localhost` and `capacitor://localhost`.

## Notes
- iOS builds require macOS + Xcode.
- Icons/splash: edit `assets/icon.png` / `assets/splash.png`, then
  `npx @capacitor/assets generate`.
```

- [ ] **Step 2: Commit**

```bash
cd /opt/spt-mentoring
git add mobile/README.md
git commit -m "docs(mobile): add Capacitor build-and-sync runbook"
```

---

## Self-Review

**Spec coverage:**
- App store presence → app shells produced (Tasks 6, 7); store *submission* is Plan 4. ✓ (foundation)
- App-like feel / branding → icon + splash (Task 5), applied per-platform (Tasks 6, 7). ✓
- Reuse existing platform → bundling `frontend/dist`, no API changes (Tasks 3, 4). ✓
- Connectivity gotchas → WebSocket base URL (Task 2), CORS origin (Task 4). ✓
- Video verify-early with fallback → Task 7 Step 4 decision gate. ✓
- Native push → **out of scope for Plan 1** (Plan 2 + 3). ✓ intentional.
- iOS on Mac / Android buildable → Tasks 6–7. ✓

**Placeholder scan:** no TBD/TODO; the one conditional ("if video fails, use browser fallback") is a concrete, specified branch. ✓

**Type consistency:** `wsBase()` defined in Task 2 and consumed in Task 2 Step 5; env vars `VITE_API_URL`/`VITE_WS_URL` consistent across Tasks 2, 6. ✓

**Known assumption to verify during execution:** `@capacitor/assets` current major (invoked as `npx @capacitor/assets generate`) — confirm the installed version's CLI flags at Task 6 Step 2; adjust flag names if the tool changed.
