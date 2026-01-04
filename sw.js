const CACHE_NAME = 'financas-app-v1';
const urlsToCache = [
    '/', 'index.html', 'manifest.json', 'icon-192.png', 'icon-512.png',
    'https://pyscript.net/releases/2024.9.1/core.js', 'https://pyscript.net/releases/2024.9.1/core.css'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request).then(response => response || fetch(event.request))
    );
});