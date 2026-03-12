/**
 * SPT Mentoring Platform – Service Worker
 * Handles Web Push notification display and click routing.
 */

self.addEventListener('push', (event) => {
  if (!event.data) return;

  let payload;
  try {
    payload = event.data.json();
  } catch {
    payload = { title: 'SPT Mentoring', body: event.data.text(), link: '/' };
  }

  const options = {
    body: payload.body || '',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    data: { link: payload.link || '/' },
    vibrate: [200, 100, 200],
    tag: payload.type || 'general',
    renotify: true,
  };

  event.waitUntil(
    self.registration.showNotification(payload.title || 'SPT Mentoring', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const link = event.notification.data?.link || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) {
          client.navigate(link);
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(link);
    })
  );
});

// Cache-first for static assets, network-first for API calls
self.addEventListener('fetch', (event) => {
  // Only handle same-origin requests
  if (!event.request.url.startsWith(self.location.origin)) return;
  // Skip API calls (always fresh)
  if (event.request.url.includes('/api/')) return;
});
