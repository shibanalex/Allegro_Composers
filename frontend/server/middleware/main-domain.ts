// With an own domain configured (NUXT_PUBLIC_SITE_URL), pages opened at another address (…onrender.com)
// move there permanently, so search engines keep one copy of the site. The API and health checks are left alone.
export default defineEventHandler((event) => {
  const configured = String(useRuntimeConfig(event).public.siteUrl || '')
  if (!configured || event.method !== 'GET') return
  const url = getRequestURL(event, { xForwardedHost: true, xForwardedProto: true })
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/_nuxt/') || url.pathname.startsWith('/media/')) return
  const main = new URL(configured)
  if (url.host === main.host) return
  return sendRedirect(event, `${main.origin}${url.pathname}${url.search}`, 301)
})
