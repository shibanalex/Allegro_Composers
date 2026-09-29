// Where the server (SSR) reaches the API: dev_server locally, the nginx gateway in docker
const apiInternal = process.env.NUXT_API_INTERNAL || 'http://127.0.0.1:8000'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  modules: ['@pinia/nuxt'],
  css: ['~/assets/css/styles.css'],
  postcss: {
    plugins: { tailwindcss: {}, autoprefixer: {} },
  },
  runtimeConfig: {
    apiInternal,
    // Set on the hosting as NUXT_PUBLIC_* environment variables (read at start, no rebuild needed)
    public: {
      siteUrl: '', // the site's main address, e.g. https://allegro-cantabile.ru: canonical links, sitemap, redirect from other addresses
      yandexVerification: '', // code from Yandex.Webmaster (the content of its <meta name="yandex-verification">)
      googleVerification: '', // code from Google Search Console (<meta name="google-site-verification">)
      metrikaId: '113130812', // Yandex.Metrika counter (plugins/metrika.client.ts); '' turns it off
    },
  },
  // Browser requests to /api and /media go through Nuxt in dev; in docker the gateway answers them first
  routeRules: {
    '/**': {
      headers: {
        // No other site may show ours in a frame (clickjacking) — except Yandex.Metrika's session replay
        // and click map. Browsers that know frame-ancestors use it; older ones fall back to the DENY.
        'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "frame-ancestors 'self' https://metrika.yandex.ru https://metrika.yandex.by https://metrica.yandex.com https://metrica.yandex.com.tr https://webvisor.com https://*.webvisor.com",
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        // HTTPS only, for a year (browsers ignore it on plain http, so local development is unaffected)
        'Strict-Transport-Security': 'max-age=31536000',
        // The microphone for sketches, on the site's own pages only; nothing else
        'Permissions-Policy': 'microphone=(self), camera=(), geolocation=(), payment=(), usb=()',
      },
    },
    '/api/**': { proxy: `${apiInternal}/api/**` },
    '/media/**': { proxy: `${apiInternal}/media/**` },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'ru' },
      title: 'Allegro — сообщество композиторов',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#0a0807' },
        { name: 'description', content: 'Опусы, партитуры и разборы: пространство для композиторов, исполнителей и теоретиков.' },
      ],
      link: [
        // A gold treble clef: bold and frameless for the browser tab, in a gilded frame for phones
        { rel: 'icon', href: '/favicon.ico', sizes: '48x48' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32.png' },
        // Larger copies for search results (Google asks for a square icon of 48 px or more, in multiples of 48)
        { rel: 'icon', type: 'image/png', sizes: '96x96', href: '/favicon-96.png' },
        { rel: 'icon', type: 'image/png', sizes: '192x192', href: '/favicon-192.png' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
        { rel: 'manifest', href: '/site.webmanifest' },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Old+Standard+TT:ital,wght@0,400;0,700;1,400;1,700&family=Cormorant+SC:wght@500;600&family=EB+Garamond:ital,wght@0,400;0,500;1,400;1,500&family=Great+Vibes&family=Tangerine:wght@700&family=Bodoni+Moda:ital,opsz,wght@1,6..96,700&display=swap',
        },
      ],
    },
  },
  vite: {
    optimizeDeps: { include: ['pdfjs-dist'] },
  },
})
