/**
 * eSavadh Service Worker
 * Provides offline shell caching, asset pre-fetching, and offline resilience.
 * Made by Team Avyukt
 */

const CACHE_NAME = "esavadh-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/static/css/style.css",
  "/static/css/mobile.css",
  "/static/js/main.js",
  "/static/js/offline_sync.js",
  "/static/js/camera.js",
  "/static/img/esavadh_logo.png",
  "/static/manifest.json"
];

// Install Event - Pre-cache core assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[eSavadh SW] Pre-caching offline application shell...");
      return cache.addAll(ASSETS_TO_CACHE).catch((err) => {
        console.warn("[eSavadh SW] Non-fatal pre-cache notice:", err);
      });
    })
  );
  self.skipWaiting();
});

// Activate Event - Clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("[eSavadh SW] Removing old cache:", key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Event - Network First with Cache Fallback for dynamic pages; Cache First for static assets
self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Skip non-GET requests and API calls from service worker cache (let offline_sync.js manage API syncing)
  if (req.method !== "GET" || url.pathname.startsWith("/api/")) {
    return;
  }

  // For static assets (CSS, JS, images, fonts): Cache-First Strategy
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          if (res && res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, clone));
          }
          return res;
        });
      })
    );
    return;
  }

  // For HTML navigation pages: Network-First with Cache Fallback
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, clone));
        }
        return res;
      })
      .catch(() => {
        return caches.match(req).then((cached) => {
          if (cached) return cached;
          // Fallback to cached root/dashboard if specific offline page isn't cached
          return caches.match("/");
        });
      })
  );
});
