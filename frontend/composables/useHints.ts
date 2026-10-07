/**
 * First-visit hints: small bubbles next to the parts of the interface a newcomer might not guess.
 * One at a time, in this order (what the page is about first, the header after); a hint read once is
 * remembered in the account, so it doesn't come back on another device.
 */
export const HINTS = ['wave-select', 'opus-files', 'opus-status', 'hall-settings', 'hall-tabs', 'feed', 'create', 'bell', 'profile'] as const
export type HintId = (typeof HINTS)[number]

export function useHints() {
  const { user } = useAuth()
  const api = useApi()
  // Hints whose element is on the screen right now
  const mounted = useState<HintId[]>('hints-mounted', () => [])

  const seen = (id: HintId) => !!user.value?.seen_hints?.includes(id)
  const current = computed(() => (user.value ? HINTS.find((id) => mounted.value.includes(id) && !seen(id)) : undefined))

  function remember(ids: readonly HintId[]) {
    if (!user.value) return
    user.value.seen_hints = [...new Set([...(user.value.seen_hints || []), ...ids])]
    api('/api/users/me/hints', { method: 'POST', body: { hints: ids } }).catch(() => {})
  }

  return {
    current,
    show: (id: HintId) => { if (!mounted.value.includes(id)) mounted.value = [...mounted.value, id] },
    hide: (id: HintId) => { mounted.value = mounted.value.filter((x) => x !== id) },
    done: (id: HintId) => remember([id]),
    doneAll: () => remember(HINTS),
    async again() {
      await api('/api/users/me/hints', { method: 'DELETE' })
      if (user.value) user.value.seen_hints = []
    },
  }
}
