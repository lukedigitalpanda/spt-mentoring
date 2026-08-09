// Returns the WebSocket origin (scheme + host, no trailing slash, no path).
// In the bundled mobile app the page origin is `localhost`, so the real
// backend must be supplied via VITE_WS_URL at build time. On the website
// VITE_WS_URL is unset and we derive it from the current page origin.
export function wsBase(): string {
  const configured = import.meta.env.VITE_WS_URL;
  if (configured) return configured;
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${location.host}`;
}
