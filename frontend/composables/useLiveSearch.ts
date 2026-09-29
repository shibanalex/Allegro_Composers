import type { UserBrief } from '~/utils/types'

export interface SearchItem { to: string; title: string; hint?: string | null; snippet?: string | null; icon?: string; user?: UserBrief }
export interface SearchGroup { title: string; items: SearchItem[] }

/** Search as you type (the header palette and the search field): members, works, posts, instruments */
export function useLiveSearch(limit = 5) {
  const api = useApi()
  const q = ref('')
  const loading = ref(false)
  const groups = ref<SearchGroup[]>([])
  const words = ref<string[]>([])
  const items = computed(() => groups.value.flatMap((g) => g.items))
  const active = ref(0)

  let timer: ReturnType<typeof setTimeout> | undefined
  let requestId = 0
  watch(q, (value) => {
    clearTimeout(timer)
    if (!value.trim()) {
      groups.value = []
      return
    }
    timer = setTimeout(async () => {
      const id = ++requestId
      loading.value = true
      try {
        const r = await api<any>('/api/search', { params: { q: value.trim(), limit } })
        if (id !== requestId) return
        groups.value = [
          { title: 'Участники', items: r.composers.map((u: any) => ({ to: `/@${u.username}`, title: u.display_name, hint: u.pseudonym || u.bio, user: u })) },
          { title: 'Сочинения', items: r.opuses.map((o: any) => ({ to: `/opus/${o.slug}`, title: o.title, snippet: o.snippet, hint: [o.subtitle, o.author.display_name].filter(Boolean).join(' · '), icon: '♪' })) },
          { title: 'Записи и статьи', items: r.posts.map((p: any) => ({
            to: `/posts/${p.slug}`,
            title: p.title || `Запись от ${formatDate(p.created_at)}`,
            snippet: p.snippet,
            hint: `${POST_KINDS[p.kind]} · ${p.author.display_name}`,
            icon: '¶',
          })) },
          { title: 'Инструменты', items: r.instruments.map((t: string) => ({ to: `/search?q=${encodeURIComponent(t)}`, title: t, hint: 'сочинения с этим инструментом', icon: '♩' })) },
        ].filter((g) => g.items.length)
        words.value = r.words || []
        active.value = 0
      } catch {
        groups.value = []
      } finally {
        if (id === requestId) loading.value = false
      }
    }, 180)
  })

  const move = (d: number) => {
    if (items.value.length) active.value = (active.value + d + items.value.length) % items.value.length
  }

  return { q, loading, groups, words, items, active, move }
}
