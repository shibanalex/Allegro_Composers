export const TOKEN_COOKIE = 'allegro_token'

/** $fetch bound to the API: same-origin in the browser, the internal address during SSR; adds the JWT. */
export function useApi() {
  const config = useRuntimeConfig()
  const token = useCookie<string | null>(TOKEN_COOKIE)
  return $fetch.create({
    baseURL: import.meta.server ? config.apiInternal : '',
    onRequest({ options }) {
      if (!token.value) return
      const headers = new Headers(options.headers as HeadersInit | undefined)
      headers.set('Authorization', `Bearer ${token.value}`)
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
