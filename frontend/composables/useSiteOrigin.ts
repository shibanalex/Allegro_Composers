/** The site's main address without a trailing slash: the configured one (own domain) or the address the page was opened at */
export function useSiteOrigin() {
  const configured = String(useRuntimeConfig().public.siteUrl || '')
  const url = useRequestURL({ xForwardedHost: true, xForwardedProto: true })
  return (configured || url.origin).replace(/\/+$/, '')
}
