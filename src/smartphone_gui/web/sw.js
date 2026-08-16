// Minimaler Service Worker fuer PWA-Startbildschirm.
// WICHTIG: Bei JEDER Aenderung an den Web-Dateien CACHE_NAME hochzaehlen,
// sonst liefert der Cache-first-Fetch unten ewig die alte Version aus!
const CACHE_NAME = 'robot-gui-v3';   // v3: echter Explorer-Preflight + Abdeckung
const ASSETS = ['/', '/index.html', '/styles.css', '/app.js',
                '/manifest.webmanifest', '/icon.svg', '/icon-180.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).catch(() => null));
  self.skipWaiting();   // neue Version sofort aktivieren
});

self.addEventListener('activate', (event) => {
  // Alte Cache-Versionen entfernen, sonst gewinnt weiter der v1-Cache.
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
