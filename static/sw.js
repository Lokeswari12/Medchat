/* CancerScreen AI — Service Worker v3 (Full Offline PWA) */

const CACHE_VER    = 'cancerscreen-v3';
const STATIC_CACHE = CACHE_VER + '-static';
const PAGE_CACHE   = CACHE_VER + '-pages';
const CDN_CACHE    = CACHE_VER + '-cdn';

/* ── Assets pre-cached on install ── */
const PRECACHE_STATIC = [
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/i18n.js',
];

const PRECACHE_PAGES = [
  '/',
  '/upload',
  '/chat',
  '/dashboard',
  '/history',
  '/risk-calculator',
  '/symptom-checker',
  '/prevention',
  '/find-specialists',
];

/* ── Offline fallback page ── */
const OFFLINE_PAGE = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline — CancerScreen AI</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:'Inter',system-ui,sans-serif;background:#f0f9ff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
  .card{background:#fff;border-radius:20px;padding:40px;max-width:440px;width:100%;text-align:center;box-shadow:0 20px 60px rgba(15,23,42,.12)}
  .icon{width:72px;height:72px;background:linear-gradient(135deg,#0ea5e9,#06b6d4);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;font-size:30px}
  h1{font-size:22px;font-weight:800;color:#0f172a;margin-bottom:8px}
  p{font-size:14px;color:#64748b;line-height:1.6;margin-bottom:24px}
  .badge{display:inline-flex;align-items:center;gap:6px;background:#fef3c7;color:#92400e;padding:6px 14px;border-radius:99px;font-size:12px;font-weight:600;margin-bottom:20px}
  .features{list-style:none;text-align:left;background:#f0f9ff;border-radius:12px;padding:16px;margin-bottom:24px}
  .features li{font-size:13px;color:#475569;padding:4px 0;display:flex;align-items:center;gap:8px}
  .features li::before{content:'✓';color:#0ea5e9;font-weight:700}
  button{background:linear-gradient(135deg,#0ea5e9,#06b6d4);color:#fff;border:none;padding:12px 28px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;width:100%}
  button:hover{opacity:.9}
</style>
</head>
<body>
<div class="card">
  <div class="icon">🧬</div>
  <span class="badge">⚠ No Internet Connection</span>
  <h1>You're Offline</h1>
  <p>CancerScreen AI needs an internet connection for AI analysis. Your previously visited pages are saved and available below.</p>
  <ul class="features">
    <li>Cached pages load instantly offline</li>
    <li>History &amp; past results are available</li>
    <li>AI chat requires internet connection</li>
    <li>All data auto-syncs when back online</li>
  </ul>
  <button onclick="location.reload()">🔄 Try Again</button>
</div>
</body>
</html>`;

/* ── Offline API response ── */
function offlineApiResponse(url) {
  if (url.includes('/api/chat')) {
    return new Response(JSON.stringify({
      reply: "You're offline. AI chat requires an internet connection. Please reconnect and try again.",
      offline: true
    }), { headers: { 'Content-Type': 'application/json' } });
  }
  if (url.includes('/api/risk-calculate')) {
    return new Response(JSON.stringify({
      error: 'offline',
      offline: true,
      overall_score: 0,
      risk_level: 'Unknown',
      top_risks: [],
      key_risk_factors: [],
      recommended_screenings: [],
      lifestyle_advice: [],
      summary: "You're offline. Please reconnect to calculate your risk."
    }), { headers: { 'Content-Type': 'application/json' } });
  }
  if (url.includes('/api/symptom-check')) {
    return new Response(JSON.stringify({
      error: 'offline',
      offline: true,
      urgency: 'Unknown',
      possible_cancers: [],
      recommended_tests: [],
      summary: "You're offline. Please reconnect to check symptoms."
    }), { headers: { 'Content-Type': 'application/json' } });
  }
  return new Response(JSON.stringify({ error: 'offline', offline: true }),
    { headers: { 'Content-Type': 'application/json' } });
}

/* ════════════════  INSTALL  ════════════════ */
self.addEventListener('install', e => {
  e.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then(c => c.addAll(PRECACHE_STATIC).catch(() => {})),
      caches.open(PAGE_CACHE).then(c => c.addAll(PRECACHE_PAGES).catch(() => {})),
    ])
  );
  self.skipWaiting();
});

/* ════════════════  ACTIVATE  ════════════════ */
self.addEventListener('activate', e => {
  const currentCaches = [STATIC_CACHE, PAGE_CACHE, CDN_CACHE];
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => !currentCaches.includes(k)).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

/* ════════════════  FETCH  ════════════════ */
self.addEventListener('fetch', e => {
  const { request } = e;
  const url = request.url;

  // Only handle GET
  if (request.method !== 'GET') return;

  // ── API calls: network only, offline JSON fallback ──
  if (url.includes('/api/')) {
    e.respondWith(
      fetch(request).catch(() => offlineApiResponse(url))
    );
    return;
  }

  // ── Static assets: cache first ──
  if (url.includes('/static/')) {
    e.respondWith(
      caches.open(STATIC_CACHE).then(c =>
        c.match(request).then(cached => {
          const net = fetch(request).then(res => {
            if (res.ok) c.put(request, res.clone());
            return res;
          }).catch(() => null);
          return cached || net;
        })
      )
    );
    return;
  }

  // ── CDN (fonts, FA, chart.js): stale-while-revalidate ──
  if (url.includes('cdn') || url.includes('fonts.g') || url.includes('cdnjs')) {
    e.respondWith(
      caches.open(CDN_CACHE).then(c =>
        c.match(request).then(cached => {
          const net = fetch(request).then(res => {
            if (res.ok) c.put(request, res.clone());
            return res;
          }).catch(() => null);
          return cached || net;
        })
      )
    );
    return;
  }

  // ── Pages: network first, cache fallback, offline page ──
  e.respondWith(
    fetch(request)
      .then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(PAGE_CACHE).then(c => c.put(request, clone));
        }
        return res;
      })
      .catch(() =>
        caches.match(request).then(cached => {
          if (cached) return cached;
          // Return offline page for navigation requests
          if (request.destination === 'document' || request.headers.get('Accept')?.includes('text/html')) {
            return new Response(OFFLINE_PAGE, {
              headers: { 'Content-Type': 'text/html; charset=utf-8' }
            });
          }
          return new Response('Offline', { status: 503 });
        })
      )
  );
});

/* ── Background sync: notify clients when back online ── */
self.addEventListener('message', e => {
  if (e.data === 'SKIP_WAITING') self.skipWaiting();
});
