# Native Mobile Apps (iOS + Android) — Design

**Date:** 2026-08-09
**Status:** Approved — ready for implementation planning
**Author:** Luke + Claude

## Goal

Turn the existing SPT Mentoring platform into installable iOS and Android
apps for mentors and scholars, carrying over the existing branding. The apps
must deliver three things the current mobile website cannot:

1. **App store presence** — findable/installable from the Apple App Store and
   Google Play (credibility with schools, scholars, funders).
2. **Reliable push notifications** — proper native push to phones (iOS web
   push is effectively unusable, which is the core reason for going native).
3. **A genuine app-like feel** — home-screen icon, splash, native chrome-free UI.

Explicitly **not** a driver: deep native device features (biometrics, offline
write, camera-heavy workflows). This shaped the approach — we are not paying the
cost of a full native rewrite for features we don't need.

## Approach: Capacitor wrapper around the existing React frontend

Capacitor packages the **existing, deployed React frontend** as native iOS and
Android apps. The web UI is the single source of truth; the native projects are
thin shells that add store packaging and native plugins (push, splash, status
bar).

### Why this over the alternatives

- **Full React Native rewrite (rejected):** would mean maintaining two entire
  frontends forever — every feature and fix done twice — for native device
  features we don't need. Months to reach parity with what the web app already does.
- **PWA only (rejected):** fails the top requirement — no real App Store / Play
  Store presence, and iOS PWA push is unreliable.
- **Capacitor (chosen):** the only option that hits all three goals without
  doubling the maintenance burden, and it reuses the platform already built.

### The abandoned Expo scaffold

The current `mobile/` directory holds a half-started Expo/React Native scaffold
(dated March, never committed, internally inconsistent — config declares
`expo-router` but code uses React Navigation). It is **removed and replaced** by
the Capacitor project. It is not carried forward.

## Architecture

```
frontend/  (existing React app — UNCHANGED, single source of truth)
   └── build → dist/
                 └── copied into ↓
mobile/  (NEW: Capacitor project — native iOS + Android shells + native plugins)
   ├── ios/        (Xcode project → App Store)
   └── android/    (Android Studio project → Google Play)
backend/  (existing Django API — one small addition for native push)
```

### How content loads

- **The compiled React frontend is bundled locally inside the app** (Capacitor
  serves the built assets from within the app bundle). The UI ships with the
  app: instant load, resilient to flaky connections, and compliant with Apple's
  rejection of apps that are merely a browser pointed at a website.
- **API calls go to the existing Django backend over HTTPS**, exactly as the
  website already does — same endpoints, same token auth. The app is just
  another API client. **No changes to the core API.**
- **Consequence:** UI changes require an app rebuild/release to reach installed
  apps (`npm run build && npx cap sync`). Backend/API and content changes remain
  live instantly, as today. Over-the-air web-layer updates are explicitly
  **out of scope for v1**.

## Push notifications (the main new work)

Native push is a different pipe than the existing web push (VAPID/`sw.js`),
which is why it needs backend work.

- **Channels:** APNs (iOS) and FCM (Android) via Capacitor's Push Notifications
  plugin. These are the reliable OS-native channels.
- **One-time setup:** a Firebase project (free) for the SPT org providing FCM +
  APNs relay, plus an APNs auth key from the (existing) Apple Developer account.
- **Backend addition:** a new endpoint + model to register a device's push token
  against the logged-in user (`POST /api/devices/`), and a native-push delivery
  path that fires FCM/APNs on the relevant events. This is a **new delivery
  channel alongside the existing email/web-push channels** — it reuses the
  notification *triggers* that already exist (from the notifications sprint), not
  new events.
- **In-app plumbing:** on login, request notification permission, obtain the
  token, register it; on notification tap, deep-link to the correct screen
  (e.g. the relevant conversation).

### Push scope for v1

Native push wired for the **top 3 engagement events only**:

1. New direct message
2. Session reminder
3. Forum reply to a matched mentor

All other notification types continue via email/web push as they do today, and
can be added to the native channel later. This is the highest-effort part of the
project and the token-storage / FCM-APNs-send / tap-routing code is genuinely
new and must be verified on real devices.

## Branding & native assets

The identity carries over for free because the app *is* the existing React UI
(same logo `sptlogo.webp`, same purple palette `#6b21a8` / `#9333ea`). Native
apps additionally require:

- **App icon** — generated at all iOS/Android sizes from the logo on a branded
  background.
- **Splash screen** — purple background + logo, shown while the UI loads.
- **Store listing assets** — app name ("SPT Mentoring"), short/long description,
  and screenshots at Apple's and Google's mandated sizes.

**Asset to gather:** a high-res/vector logo (SVG or large PNG) produces much
crisper icons than upscaling the `.webp`. If unavailable, we work from what we have.

## Video calls (JaaS) — verify-early with fallback

JaaS runs as a web SDK. Inside a native webview it can work but needs native
**camera + microphone permission plumbing** (iOS is strict; missing permission
strings are a common rejection cause).

- **Milestone:** treat "video calls working in-app" as an explicit verification
  milestone **early** in the build.
- **Fallback:** if it hits a wall, v1 falls back to opening video calls in the
  device browser, with a proper in-app fix as a fast-follow. A video snag must
  not hold up the whole app.

## Build & release pipeline

- **Store accounts:** Apple Developer + Google Play both already set up under SPT
  — no publishing blocker.
- **Android** (`.aab`) can be built end-to-end here or in cloud CI.
- **iOS** requires macOS + Xcode (Apple's rule; this server is Linux). The code
  is structured fully ready; the iOS compile-and-submit step runs wherever
  Mac/cloud access exists (a Mac, or a cloud macOS build service such as EAS
  Build / Codemagic on a modest paid tier). **Decision still open:** which iOS
  build path to use — does not block any build work.

## v1 scope

| In v1 | Deferred (fast-follow) |
|---|---|
| Full existing platform in-app (messaging, forums, profiles, sessions) — free via the wrapper | Over-the-air web-layer updates |
| Native push for top 3 events (DM, session reminder, forum reply) | Native push for remaining notification types |
| Branded icon + splash + store listings | Deep native features (biometrics, offline write) |
| Video calls verified in-app (with browser fallback) | Tablet-optimised layouts |
| Both stores submission-ready | |

## Testing

- **Unit-level (TDD, matching existing backend conventions):** the new device
  registration endpoint and push delivery path.
- **Real-device verification checklist** (cannot be fully proven without physical
  hardware): push delivery, notification tap-routing, video camera/mic
  permissions, and login/auth flow on both platforms.

## Open decisions

1. **iOS build path** — Mac vs. cloud macOS build service. Does not block build work.
2. **High-res logo availability** — affects icon crispness only.
