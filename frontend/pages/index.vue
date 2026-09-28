<template>
  <div>
    <!-- Hero -->
    <!-- Hero: compact, so the whole feed panel fits on the first screen -->
    <section class="relative flex flex-col items-center px-6 pb-5 pt-2 text-center">
      <div class="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[14rem] w-[14rem] max-w-full -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgb(var(--c-gold)/0.14),transparent_65%)] blur-2xl" />
      <h1 class="title-script brand animate-fade-up text-[4rem] leading-none sm:text-[4.5rem]">Allegro</h1>
      <p class="eyebrow mt-1 animate-fade-up" style="animation-delay: .1s">Сообщество композиторов</p>
    </section>

    <div class="grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <!-- The feed: everything new in the members' halls, in one panel that scrolls on its own -->
      <section class="feed-panel mx-auto w-full max-w-3xl" aria-label="Лента">
        <header class="border-b border-gold/15 px-3 py-4 sm:px-5">
          <nav class="flex flex-wrap justify-center gap-2" aria-label="Что показывать в ленте">
            <button
              v-for="f in FILTERS"
              :key="f.id"
              type="button"
              class="chip"
              :class="{ active: kind === f.id }"
              :aria-pressed="kind === f.id"
              @click="choose(f.id)"
            >
              {{ f.label }}
            </button>
          </nav>
          <div v-if="user" class="mt-3 flex flex-wrap justify-center gap-2">
            <NuxtLink v-if="can('publish_opus')" to="/create/opus" class="btn-secondary px-4 py-1.5 text-sm">+ Сочинение</NuxtLink>
            <NuxtLink v-if="can('publish_performance')" :to="`/@${user.username}?tab=performances`" class="btn-secondary px-4 py-1.5 text-sm">+ Исполнение</NuxtLink>
            <NuxtLink v-if="can('publish_article')" to="/create/post?kind=article" class="btn-secondary px-4 py-1.5 text-sm">+ Статья</NuxtLink>
            <NuxtLink :to="`/@${user.username}?tab=blog`" class="btn-secondary px-4 py-1.5 text-sm">+ Запись</NuxtLink>
          </div>
        </header>

        <div ref="scroller" class="feed-panel-body">
          <EmptyState v-if="!items.length && !loading">{{ EMPTY[kind] }}</EmptyState>
          <div class="space-y-5" :class="{ 'opacity-60 transition': loading && !items.length }">
            <FeedItem v-for="item in items" :key="`${item.type}-${item.opus?.id || item.performance?.id || item.post?.id}`" :item="item" />
          </div>
          <!-- Reaching this line loads the next page; the button is for keyboards and old browsers -->
          <div v-if="nextBefore" ref="sentinel" class="py-8 text-center">
            <button class="btn-secondary" :disabled="loading" @click="more">{{ loading ? 'Загрузка…' : 'Показать ещё' }}</button>
          </div>
          <p v-else-if="items.length" class="py-8 text-center font-elegant italic text-parchment-faint">Это всё — дальше тишина</p>
        </div>
      </section>

      <!-- Members: whose halls the feed comes from -->
      <aside v-if="members.length">
        <div class="lg:sticky lg:top-28">
          <p class="eyebrow mb-4">Участники</p>
          <ul class="space-y-3">
            <li v-for="m in members" :key="m.id">
              <NuxtLink :to="`/@${m.username}`" class="group flex items-center gap-3">
                <UserAvatar :user="m" :size="40" />
                <span class="min-w-0">
                  <span class="block truncate font-display italic text-parchment transition group-hover:text-gold-light">{{ m.display_name }}</span>
                  <span class="block truncate text-sm text-parchment-faint">{{ ROLES[m.role]?.label }}</span>
                </span>
              </NuxtLink>
            </li>
          </ul>
          <NuxtLink to="/about" class="mt-6 inline-block font-caps text-sm font-semibold tracking-[0.15em] text-gold transition hover:text-gold-light">О сообществе →</NuxtLink>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FeedEntry, Profile } from '~/utils/types'

useSeoMeta({
  title: 'Allegro — сообщество композиторов',
  description: 'Сообщество композиторов, теоретиков и исполнителей: новые сочинения с партитурами и записями, исполнения, статьи и блоги.',
})

type Kind = 'all' | 'works' | 'performances' | 'articles' | 'blogs'
const FILTERS: { id: Kind; label: string }[] = [
  { id: 'all', label: 'Всё' },
  { id: 'works', label: 'Сочинения' },
  { id: 'performances', label: 'Исполнения' },
  { id: 'articles', label: 'Статьи и обзоры' },
  { id: 'blogs', label: 'Блоги' },
]
const EMPTY: Record<Kind, string> = {
  all: 'В залах пока тихо',
  works: 'Новых сочинений пока нет',
  performances: 'Исполнений пока нет',
  articles: 'Статей пока нет',
  blogs: 'Записей пока нет',
}

const api = useApi()
const route = useRoute()
const router = useRouter()
const { user, can } = useAuth()

// The chosen filter lives in the address (?feed=works), so a filtered feed can be shared
const valid = (v: unknown): Kind => (FILTERS.some((f) => f.id === v) ? (v as Kind) : 'all')
const kind = ref<Kind>(valid(route.query.feed))

interface FeedPage { items: FeedEntry[]; next_before: string | null }
const { data, pending } = await useAsyncData(
  'feed',
  () => api<FeedPage>('/api/feed', { params: { kind: kind.value, limit: 15 } }),
  { watch: [kind] },
)
const extra = ref<FeedEntry[]>([])
const cursor = ref<string | null>(null)
const items = computed(() => [...(data.value?.items || []), ...extra.value])
const nextBefore = computed(() => (extra.value.length ? cursor.value : data.value?.next_before) || null)
const loadingMore = ref(false)
const loading = computed(() => pending.value || loadingMore.value)

watch(kind, () => {
  extra.value = []
  cursor.value = null
})

const scroller = ref<HTMLElement>()
const sentinel = ref<HTMLElement>()

function choose(id: Kind) {
  kind.value = id
  scroller.value?.scrollTo({ top: 0 })
  router.replace({ query: { ...route.query, feed: id === 'all' ? undefined : id } })
}

// The next page loads a little before the end is reached. The viewport is the observer's root:
// the panel's own scrolling clips the sentinel too, so this works both with and without it.
let observer: IntersectionObserver | undefined
onMounted(() => {
  observer = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) more()
  }, { rootMargin: '0px 0px 600px 0px' })
  watch(sentinel, (el, old) => {
    if (old) observer?.unobserve(old)
    if (el) observer?.observe(el)
  }, { immediate: true })
})
onBeforeUnmount(() => observer?.disconnect())

async function more() {
  if (!nextBefore.value || loading.value) return
  loadingMore.value = true
  try {
    const page = await api<FeedPage>('/api/feed', { params: { kind: kind.value, limit: 15, before: nextBefore.value } })
    extra.value.push(...page.items)
    cursor.value = page.next_before
  } finally {
    loadingMore.value = false
  }
}

const { data: memberData } = await useAsyncData('members', () => api<Profile[]>('/api/users').catch(() => [] as Profile[]))
const members = computed(() => memberData.value || [])
</script>
