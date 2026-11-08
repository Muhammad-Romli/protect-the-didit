// Service worker: lets the game start without a connection after the first full online run.
// Own files: network first (so updates arrive), cache as fallback. pygbag runtime on its CDN: cache first.
const CACHE = 'ptd-v1';
const CDN = 'pygame-web.github.io';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || req.headers.has('range')) return;
  const url = new URL(req.url);
  const own = url.origin === self.location.origin;
  if (!own && url.hostname !== CDN) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const store = (res) => { if (res && res.status === 200) cache.put(req, res.clone()); return res; };
    if (own) {
      try { return store(await fetch(req)); } catch (err) { return (await cache.match(req)) || Response.error(); }
    }
    const hit = await cache.match(req);
    if (hit) return hit;
    return store(await fetch(req));
  })());
});
