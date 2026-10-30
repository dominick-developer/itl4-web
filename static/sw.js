const CACHE_NAME = 'itl4-v3';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((names) => Promise.all(
            names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))
        )).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;
    if (!event.request.url.startsWith('http')) return;
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                if (response && response.status === 200) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                }
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});

self.addEventListener('push', (event) => {
    let data = {};
    try { data = event.data ? event.data.json() : {}; } catch (e) {}
    const title = data.title || 'IT Level 4 Connect';
    const options = {
        body: data.body || '',
        icon: '/static/icon-192.png',
        badge: '/static/icon-192.png',
        tag: data.tag || 'timetable',
        data: { url: data.url || '/timetable' },
        vibrate: [200, 100, 200],
        requireInteraction: false,
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = event.notification.data.url || '/';
    event.waitUntil(clients.matchAll({ type: 'window' }).then((cs) => {
        for (const c of cs) {
            if (c.url.includes(url) && 'focus' in c) return c.focus();
        }
        if (clients.openWindow) return clients.openWindow(url);
    }));
});