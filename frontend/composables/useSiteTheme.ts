import type { HallTheme } from '~/utils/types'

const THEMES: HallTheme[] = ['baroque', 'romantic', 'modern', 'avantgarde']

/**
 * The style of the whole site for this visitor: chosen in the header, kept in a cookie (so the server
 * renders the page in it at once). Until they choose, a member sees the style of their own hall and a
 * guest romanticism. A member's hall is always shown in its owner's style (pages/@[username].vue).
 */
export function useSiteTheme() {
  const cookie = useCookie<string | null>('allegro-theme', { maxAge: 60 * 60 * 24 * 365, sameSite: 'lax' })
  const { user } = useAuth()
  const theme = computed<HallTheme>(() => {
    const chosen = cookie.value as HallTheme
    if (THEMES.includes(chosen)) return chosen
    return user.value?.hall_theme || 'romantic'
  })
  return {
    themes: THEMES,
    theme,
    chosen: computed(() => THEMES.includes(cookie.value as HallTheme)),
    setTheme: (value: HallTheme | null) => (cookie.value = value),
  }
}
