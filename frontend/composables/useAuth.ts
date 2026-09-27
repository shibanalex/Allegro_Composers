import type { Me } from '~/utils/types'

interface TokenOut { access_token: string; user: Me }

export function useAuth() {
  const user = useState<Me | null>('auth-user', () => null)
  // While the community is invite-only the backend refuses sign-ups; the site then hides every way to register
  const registrationOpen = useState('auth-registration-open', () => false)
  // A freshly deployed site with no accounts yet: /setup creates the first one (with the code from the hosting settings)
  const setupAvailable = useState('auth-setup-available', () => false)
  const token = useCookie<string | null>(TOKEN_COOKIE, {
    maxAge: 60 * 60 * 24 * 14,
    sameSite: 'lax',
    secure: import.meta.client && location.protocol === 'https:',
  })
  const api = useApi()

  const accept = (result: TokenOut) => {
    token.value = result.access_token
    user.value = result.user
  }

  return {
    user,
    loggedIn: computed(() => !!user.value),
    registrationOpen,
    setupAvailable,
    async fetchConfig() {
      try {
        const config = await api<{ registration_open: boolean; setup_available: boolean }>('/api/auth/config')
        registrationOpen.value = config.registration_open
        setupAvailable.value = config.setup_available
      } catch {
        registrationOpen.value = false
        setupAvailable.value = false
      }
    },
    async fetchMe() {
      if (!token.value) return (user.value = null)
      try {
        user.value = await api<Me>('/api/auth/me')
      } catch {
        token.value = null
        user.value = null
      }
    },
    async login(login: string, password: string) {
      accept(await api<TokenOut>('/api/auth/login', { method: 'POST', body: { login, password } }))
    },
    async register(body: { username: string; email: string; password: string; display_name: string }) {
      accept(await api<TokenOut>('/api/auth/register', { method: 'POST', body }))
    },
    async setup(body: { code: string; username: string; email: string; password: string; display_name: string }) {
      accept(await api<TokenOut>('/api/auth/setup', { method: 'POST', body }))
      setupAvailable.value = false
    },
    logout() {
      token.value = null
      user.value = null
    },
  }
}
