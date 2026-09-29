// Allegro's service worker: shows push notifications (even when the site is closed) and opens the page
// a notification is about. It does nothing else — no caching, no offline mode.

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { title: 'Allegro', body: event.data ? event.data.text() : '' }
  }
  event.waitUntil(
    self.registration.showNotification(data.title || 'Allegro', {
      body: data.body || '',
      icon: '/favicon-192.png',
      badge: '/favicon-96.png',
      tag: data.tag || undefined, // the same publication replaces its notification instead of piling up
      data: { url: data.url || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  // Only the site's own pages
  const path = typeof event.notification.data?.url === 'string' && event.notification.data.url.startsWith('/') ? event.notification.data.url : '/'
  const url = new URL(path, self.location.origin).href
  event.waitUntil((async () => {
    const tabs = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    const open = tabs.find((tab) => new URL(tab.url).origin === self.location.origin)
    if (open) {
      await open.focus()
      return open.navigate(url)
    }
    return self.clients.openWindow(url)
  })())
})
