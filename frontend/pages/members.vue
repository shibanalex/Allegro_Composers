<template>
  <!-- Everyone in the community: the newest first, by role, by name -->
  <div class="mx-auto max-w-5xl pb-16">
    <PageHeader eyebrow="Allegro" title="Участники" :subtitle="subtitle" />

    <div class="mb-8 space-y-4">
      <form role="search" class="relative" @submit.prevent>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-gold/70"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
        <input v-model="query" type="search" class="field !pl-12 font-elegant text-lg" placeholder="Имя, псевдоним или адрес зала" aria-label="Найти участника" autocomplete="off">
      </form>
      <nav class="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 [scrollbar-width:none] sm:mx-0 sm:flex-wrap sm:px-0" aria-label="Роль">
        <button
          v-for="r in ROLE_FILTERS"
          :key="r.id"
          type="button"
          class="chip shrink-0 whitespace-nowrap"
          :class="{ active: role === r.id }"
          :aria-pressed="role === r.id"
          @click="role = r.id"
        >
          {{ r.label }}
        </button>
      </nav>
    </div>

    <EmptyState v-if="!pending && !items.length">{{ query.trim() ? 'Никого не нашлось' : 'Здесь пока никого нет' }}</EmptyState>
    <ul class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" :class="{ 'opacity-60 transition-opacity': pending }">
      <li v-for="m in items" :key="m.id">
        <NuxtLink :to="`/@${m.username}`" class="card group flex h-full items-start gap-4 !p-5 transition hover:border-gold/40">
          <UserAvatar :user="m" :size="56" class="shrink-0" />
          <span class="min-w-0 leading-tight">
            <span class="block truncate font-display text-xl italic text-parchment transition group-hover:text-gold-light">{{ m.display_name }}</span>
            <span v-if="m.pseudonym" class="block truncate font-elegant italic text-gold-light/90">{{ m.pseudonym }}</span>
            <span class="mt-1 block text-sm text-parchment-faint">{{ ROLES[m.role || 'listener']?.label }}<template v-if="activity(m)"> · {{ activity(m) }}</template></span>
            <span v-if="m.bio" class="mt-2 line-clamp-2 block text-sm leading-snug text-parchment-muted">{{ m.bio }}</span>
          </span>
        </NuxtLink>
      </li>
    </ul>

    <div v-if="items.length < total" class="mt-8 text-center">
      <button type="button" class="btn-secondary" :disabled="loadingMore" @click="more">{{ loadingMore ? 'Загружаю…' : 'Показать ещё' }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Profile } from '~/utils/types'

interface MemberPage { items: Profile[]; total: number }

const ROLE_FILTERS = [
  { id: '', label: 'Все' },
  { id: 'composer', label: 'Композиторы' },
  { id: 'theorist', label: 'Теоретики' },
  { id: 'performer', label: 'Исполнители' },
  { id: 'listener', label: 'Слушатели' },
]
const PAGE = 24

const route = useRoute()
const router = useRouter()
const api = useApi()

// The role and the search live in the address: a filtered list can be shared and survives «назад»
const role = ref(typeof route.query.role === 'string' && ROLE_FILTERS.some((r) => r.id === route.query.role) ? route.query.role : '')
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const search = ref(query.value.trim())
let typing: ReturnType<typeof setTimeout> | undefined
watch(query, (v) => {
  clearTimeout(typing)
  typing = setTimeout(() => (search.value = v.trim()), 300)
})
watch([role, search], () => {
  router.replace({ query: { ...(role.value ? { role: role.value } : {}), ...(search.value ? { q: search.value } : {}) } })
})

const { data, pending } = await useAsyncData('members', () =>
  api<MemberPage>('/api/users', { params: { limit: PAGE, ...(role.value ? { role: role.value } : {}), ...(search.value ? { q: search.value } : {}) } }),
{ watch: [role, search] })
const extra = ref<Profile[]>([])
watch(data, () => (extra.value = []))
const items = computed(() => [...(data.value?.items || []), ...extra.value])
const total = computed(() => data.value?.total || 0)

const subtitle = computed(() => {
  const n = total.value
  if (role.value || search.value) return `Нашлось: ${n}`
  return `${n} ${plural(n, 'участник', 'участника', 'участников')} — композиторы, теоретики, исполнители и слушатели`
})

const loadingMore = ref(false)
async function more() {
  loadingMore.value = true
  try {
    const page = await api<MemberPage>('/api/users', {
      params: { limit: PAGE, offset: items.value.length, ...(role.value ? { role: role.value } : {}), ...(search.value ? { q: search.value } : {}) },
    })
    extra.value.push(...page.items)
  } finally {
    loadingMore.value = false
  }
}

function activity(m: Profile) {
  const s = m.stats || {}
  const parts = [
    s.opuses && `${s.opuses} ${plural(s.opuses, 'сочинение', 'сочинения', 'сочинений')}`,
    s.performances && `${s.performances} ${plural(s.performances, 'исполнение', 'исполнения', 'исполнений')}`,
    s.articles && `${s.articles} ${plural(s.articles, 'статья', 'статьи', 'статей')}`,
  ].filter(Boolean)
  return parts.slice(0, 2).join(', ')
}

useSeoMeta({
  title: 'Участники — Allegro',
  description: 'Композиторы, теоретики, исполнители и слушатели сообщества Allegro',
})
</script>
