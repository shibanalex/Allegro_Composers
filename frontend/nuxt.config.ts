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
    },
  },
  // Browser requests to /api and /media go through Nuxt in dev; in docker the gateway answers them first
  routeRules: {
    '/**': {
      headers: {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
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
        { rel: 'icon', href: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90' fill='%23c9a36a'>♪</text></svg>" },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400;1,500&family=Cormorant+SC:wght@500;600&family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Great+Vibes&family=Tangerine:wght@700&family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap',
        },
      ],
    },
  },
  vite: {
    optimizeDeps: { include: ['pdfjs-dist'] },
  },
})
