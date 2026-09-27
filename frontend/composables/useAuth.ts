import type { Me } from '~/utils/types'

interface TokenOut { access_token: string; user: Me }

export function useAuth() {
  const user = useState<Me | null>('auth-user', () => null)
  const token = useCookie<string | null>(TOKEN_COOKIE, { maxAge: 60 * 60 * 24 * 14, sameSite: 'lax' })
  const api = useApi()

  const accept = (result: TokenOut) => {
    token.value = result.access_token
    user.value = result.user
  }

  return {
    user,
    loggedIn: computed(() => !!user.value),
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
    logout() {
      token.value = null
      user.value = null
    },
  }
}
