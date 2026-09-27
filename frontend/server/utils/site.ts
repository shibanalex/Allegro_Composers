import type { H3Event } from 'h3'

/** Main address of the site for robots.txt and sitemap.xml (see useSiteOrigin for pages) */
export function siteOrigin(event: H3Event) {
  const configured = String(useRuntimeConfig(event).public.siteUrl || '')
  return (configured || getRequestURL(event, { xForwardedHost: true, xForwardedProto: true }).origin).replace(/\/+$/, '')
}
