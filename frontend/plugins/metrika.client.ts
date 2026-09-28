// Yandex.Metrika: visits, sources, popular pages (metrika.yandex.ru). Counts the live site only, not
// development on localhost. The site changes pages without reloading, so every navigation is sent as a hit.
declare global {
  interface Window { ym?: (id: number, method: string, ...args: unknown[]) => void }
}

export default defineNuxtPlugin(() => {
  const id = Number(useRuntimeConfig().public.metrikaId)
  if (!id || ['localhost', '127.0.0.1'].includes(location.hostname)) return

  // The counter's own loader (from the Metrika settings page)
  const w = window as any
  w.ym = w.ym || function (...args: unknown[]) { (w.ym.a = w.ym.a || []).push(args) }
  w.ym.l = Date.now()
  const script = document.createElement('script')
  script.async = true
  script.src = `https://mc.yandex.ru/metrika/tag.js?id=${id}`
  document.head.appendChild(script)

  window.ym!(id, 'init', {
    ssr: true,
    webvisor: true,
    clickmap: true,
    ecommerce: 'dataLayer',
    referrer: document.referrer,
    url: location.href,
    accurateTrackBounce: true,
    trackLinks: true,
  })

  // Page changes inside the site (the first page is counted by 'init')
  const router = useRouter()
  let previous = location.href
  router.afterEach(() => {
    nextTick(() => {
      const url = location.href
      if (url === previous) return
      window.ym!(id, 'hit', url, { referer: previous, title: document.title })
      previous = url
    })
  })
})
