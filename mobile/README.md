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
