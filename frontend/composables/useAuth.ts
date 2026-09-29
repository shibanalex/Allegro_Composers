import type { Me, SiteConfig } from '~/utils/types'

interface TokenOut { user: Me }

export interface JoinBody {
  username: string
  display_name: string
  password: string
  role: string
  email?: string | null
  invite?: string | null
}

/** Who is signed in, what they may publish, and how the site lets people join */
export function useAuth() {
  const user = useState<Me | null>('auth-user', () => null)
  // How people join (by invitation for now) and whether a fresh site still needs its first account
  const config = useState<SiteConfig | null>('auth-config', () => null)
  // The login itself is an HttpOnly cookie set by the API; this readable marker only says «someone is signed in»
  const session = useCookie<string | null>('allegro_session')
  const api = useApi()

  const accept = (result: TokenOut) => {
    user.value = result.user
  }

  return {
    user,
    config,
    loggedIn: computed(() => !!user.value),
    isAdmin: computed(() => !!user.value?.is_admin),
    registrationOpen: computed(() => config.value?.registration === 'open'),
    inviteOnly: computed(() => config.value?.registration === 'invite'),
    setupAvailable: computed(() => !!config.value?.setup_available),
    /** publish_opus · publish_article · publish_performance · publish_news · manage_site */
    can: (capability: string) => !!user.value?.capabilities?.includes(capability),
    async fetchConfig() {
      try {
        config.value = await api<SiteConfig>('/api/auth/config')
      } catch {
        config.value = null
      }
    },
    async fetchMe() {
      if (!session.value) return (user.value = null)
      try {
        user.value = await api<Me>('/api/auth/me')
      } catch {
        user.value = null
      }
    },
    async login(login: string, password: string) {
      accept(await api<TokenOut>('/api/auth/login', { method: 'POST', body: { login, password } }))
    },
    async register(body: JoinBody) {
      accept(await api<TokenOut>('/api/auth/register', { method: 'POST', body }))
    },
    async setup(body: JoinBody & { code: string }) {
      accept(await api<TokenOut>('/api/auth/setup', { method: 'POST', body }))
      if (config.value) config.value.setup_available = false
    },
    async resetPassword(tokenValue: string, password: string) {
      accept(await api<TokenOut>('/api/auth/reset', { method: 'POST', body: { token: tokenValue, password } }))
    },
    /** Other devices are signed out; this one keeps working with the fresh token */
    async changePassword(current: string, next: string) {
      accept(await api<TokenOut>('/api/users/me/password', { method: 'POST', body: { current_password: current, new_password: next } }))
    },
    async signOutEverywhere() {
      accept(await api<TokenOut>('/api/users/me/sessions/revoke', { method: 'POST' }))
    },
    async logout() {
      try {
        await api('/api/auth/logout', { method: 'POST' })
      } catch {}
      session.value = null
      user.value = null
    },
  }
}
