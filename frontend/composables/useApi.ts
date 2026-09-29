/**
 * $fetch bound to the API: same-origin in the browser, the internal address during SSR.
 *
 * Signing in is an HttpOnly cookie that the API sets itself: page scripts never see the token. The browser
 * sends the cookie with every request to the site; the server rendering passes the visitor's cookie on.
 */
export function useApi() {
  const config = useRuntimeConfig()
  const cookie = import.meta.server ? useRequestHeaders(['cookie']).cookie : undefined
  return $fetch.create({
    baseURL: import.meta.server ? config.apiInternal : '',
    onRequest({ options }) {
      if (!cookie) return
      const headers = new Headers(options.headers as HeadersInit | undefined)
      headers.set('cookie', cookie)
      options.headers = headers
    },
  })
}

/** Human-readable message from a FastAPI error response */
export function apiError(error: any, fallback = 'Что-то пошло не так'): string {
  const detail = error?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d: any) => String(d.msg || '').replace(/^Value error, /, '')).join('; ')
  }
  return fallback
}
