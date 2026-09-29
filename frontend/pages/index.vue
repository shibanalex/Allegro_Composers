<template>
  <div>
    <!-- Hero -->
    <section class="relative flex flex-col items-center px-6 pb-8 pt-8 text-center">
      <div class="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[20rem] w-[20rem] max-w-full -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgb(var(--c-gold)/0.14),transparent_65%)] blur-2xl" />
      <p class="eyebrow animate-fade-up">Сообщество композиторов</p>
      <h1 class="title-script brand animate-fade-up text-[4.5rem] leading-tight sm:text-[6rem]" style="animation-delay: .1s">Allegro</h1>
      <Ornament class="-mt-2 w-48 animate-fade-up" style="animation-delay: .2s" />
      <p class="mt-4 flex flex-wrap justify-center gap-x-6 gap-y-1 font-elegant text-lg italic text-parchment-muted animate-fade-up" style="animation-delay: .3s">
        <span>{{ members.length }} {{ plural(members.length, 'участник', 'участника', 'участников') }}</span>
        <span>{{ counts.opuses }} {{ plural(counts.opuses, 'сочинение', 'сочинения', 'сочинений') }}</span>
        <span>{{ counts.posts }} {{ plural(counts.posts, 'запись', 'записи', 'записей') }}</span>
      </p>
    </section>

    <div class="grid grid-cols-[minmax(0,1fr)] items-start gap-8 lg:grid-cols-[minmax(0,1fr)_19rem] xl:grid-cols-[13rem_minmax(0,1fr)_20rem]">
      <!-- Left: what the feed shows, what one can publish, the community -->
      <aside class="sticky top-28 hidden xl:block">
        <p class="eyebrow mb-3">Лента</p>
        <nav class="space-y-1" aria-label="Что показывать в ленте">
          <button
            v-for="f in FILTERS"
            :key="f.id"
            type="button"
            class="flex w-full items-center gap-3 border-l-2 px-3 py-2 text-left font-caps text-sm font-semibold tracking-[0.12em] transition"
            :class="kind === f.id ? 'border-gold bg-gold/10 text-gold-light' : 'border-transparent text-parchment-muted hover:border-gold/40 hover:text-parchment'"
            :aria-pressed="kind === f.id"
            @click="choose(f.id)"
          >
            <span class="w-4 text-center text-gold/80" aria-hidden="true">{{ f.icon }}</span>{{ f.label }}
          </button>
        </nav>

        <template v-if="user">
          <p class="eyebrow mb-3 mt-8">Опубликовать</p>
          <div class="flex flex-col gap-2">
            <button v-if="can('publish_sketch')" type="button" class="btn-secondary justify-start px-4 py-1.5 text-sm" @click="startSketch">+ Эскиз</button>
            <NuxtLink v-for="c in creates" :key="c.to" :to="c.to" class="btn-secondary justify-start px-4 py-1.5 text-sm">{{ c.label }}</NuxtLink>
          </div>
        </template>

        <p class="eyebrow mb-3 mt-8">Сообщество</p>
        <nav class="space-y-2 font-elegant text-lg italic text-parchment-muted">
          <NuxtLink to="/about" class="block transition hover:text-gold-light">О нас</NuxtLink>
          <NuxtLink to="/about?tab=news" class="block transition hover:text-gold-light">Новости</NuxtLink>
          <NuxtLink to="/about?tab=feedback" class="block transition hover:text-gold-light">Предложения</NuxtLink>
          <NuxtLink to="/about?tab=links" class="block transition hover:text-gold-light">Ссылки</NuxtLink>
        </nav>
      </aside>

      <!-- The feed: everything new in the members' halls -->
      <section class="min-w-0" aria-label="Лента">
        <SearchBox class="mb-5" />
        <nav class="mb-4 flex flex-wrap justify-center gap-2 xl:hidden" aria-label="Что показывать в ленте">
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
        <div v-if="user" class="mb-6 flex flex-wrap justify-center gap-2 xl:hidden">
          <button v-if="can('publish_sketch')" type="button" class="btn-secondary px-4 py-1.5 text-sm" @click="startSketch">+ Эскиз</button>
          <NuxtLink v-for="c in creates" :key="c.to" :to="c.to" class="btn-secondary px-4 py-1.5 text-sm">{{ c.label }}</NuxtLink>
        </div>

        <!-- A sketch in a minute, right above the feed -->
        <SketchComposer v-if="sketching" ref="sketchPanel" class="mb-6" @close="sketching = false" @published="onSketch" />

        <EmptyState v-if="!items.length && !loading">{{ EMPTY[kind] }}</EmptyState>
        <div class="space-y-6" :class="{ 'opacity-60 transition': loading && !items.length }">
          <FeedItem v-for="item in items" :key="keyOf(item)" :item="item" @removed="removed.add(keyOf(item))" />
        </div>
        <!-- Reaching this line loads the next page; the button is for keyboards and old browsers -->
        <div v-if="nextBefore" ref="sentinel" class="py-10 text-center">
          <button class="btn-secondary" :disabled="loading" @click="more">{{ loading ? 'Загрузка…' : 'Показать ещё' }}</button>
        </div>
        <p v-else-if="items.length" class="py-10 text-center font-elegant text-lg italic text-parchment-faint">Это всё — дальше тишина</p>
      </section>

      <!-- Right: new works, members, themes -->
      <aside class="thin-scroll space-y-6 lg:sticky lg:top-28 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto">
        <section v-if="newOpuses.length" class="card !p-5">
          <h2 class="eyebrow mb-4">Новые сочинения</h2>
          <ul class="space-y-4">
            <li v-for="o in newOpuses" :key="o.id" class="group flex items-center gap-3">
              <NuxtLink :to="`/opus/${o.slug}`" class="frame frame-thin h-14 w-14 shrink-0">
                <div class="frame-inner">
                  <MediaImg v-if="o.cover_url" :src="o.cover_url" alt="" class="h-full w-full object-cover" loading="lazy" />
                  <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-ink-700 to-ink-900 font-display text-2xl italic text-gold/30">{{ o.title.charAt(0) }}</div>
                </div>
              </NuxtLink>
              <div class="min-w-0 flex-1 leading-tight">
                <NuxtLink :to="`/opus/${o.slug}`" class="block truncate font-display text-lg text-parchment transition group-hover:text-gold-light">{{ o.title }}</NuxtLink>
                <NuxtLink :to="`/@${o.author.username}`" class="block truncate text-sm text-parchment-faint transition hover:text-gold-light">{{ o.author.display_name }}</NuxtLink>
              </div>
              <PlayButton v-if="o.audio_type !== 'none'" :opus="o" size="sm" />
            </li>
          </ul>
          <button type="button" class="mt-4 font-caps text-sm font-semibold tracking-[0.15em] text-gold transition hover:text-gold-light" @click="choose('works')">Все сочинения →</button>
        </section>

        <section v-if="members.length" class="card !p-5">
          <h2 class="eyebrow mb-4">Участники</h2>
          <ul class="space-y-3">
            <li v-for="m in shownMembers" :key="m.id">
              <NuxtLink :to="`/@${m.username}`" class="group flex items-center gap-3">
                <UserAvatar :user="m" :size="44" />
                <span class="min-w-0 leading-tight">
                  <span class="block truncate font-display text-lg italic text-parchment transition group-hover:text-gold-light">{{ m.display_name }}</span>
                  <span class="block truncate text-sm text-parchment-faint">{{ ROLES[m.role]?.label }}<template v-if="activity(m)"> · {{ activity(m) }}</template></span>
                </span>
              </NuxtLink>
            </li>
          </ul>
          <p v-if="!user" class="mt-4 border-t border-gold/10 pt-4 text-sm text-parchment-faint">
            Вступить можно по приглашению участника. <NuxtLink to="/about" class="link">О сообществе</NuxtLink>
          </p>
        </section>

      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FeedEntry, Opus, Page, Profile } from '~/utils/types'

definePageMeta({ wide: true })
useSeoMeta({
  title: 'Allegro — сообщество композиторов',
  description: 'Сообщество композиторов, теоретиков и исполнителей: новые сочинения с партитурами и записями, исполнения, статьи и блоги.',
})

type Kind = 'all' | 'works' | 'sketches' | 'feedback' | 'performances' | 'articles' | 'blogs'
const FILTERS: { id: Kind; label: string; icon: string }[] = [
  { id: 'all', label: 'Всё', icon: '✦' },
  { id: 'works', label: 'Сочинения', icon: '♪' },
  { id: 'sketches', label: 'Эскизы', icon: '✐' },
  { id: 'feedback', label: 'Ждут отзыва', icon: '?' },
  { id: 'performances', label: 'Исполнения', icon: '♫' },
  { id: 'articles', label: 'Статьи и обзоры', icon: '§' },
  { id: 'blogs', label: 'Блоги', icon: '✎' },
]
const EMPTY: Record<Kind, string> = {
  all: 'В залах пока тихо',
  works: 'Новых сочинений пока нет',
  sketches: 'Эскизов пока нет',
  feedback: 'Сейчас никто не ждёт отзыва',
  performances: 'Исполнений пока нет',
  articles: 'Статей пока нет',
  blogs: 'Записей пока нет',
}

const api = useApi()
const route = useRoute()
const router = useRouter()
const { user, can } = useAuth()

const creates = computed(() => {
  if (!user.value) return []
  const hall = `/@${user.value.username}`
  return [
    can('publish_opus') && { to: '/create/opus', label: '+ Сочинение' },
    can('publish_performance') && { to: `${hall}?tab=performances`, label: '+ Исполнение' },
    can('publish_article') && { to: '/create/post?kind=article', label: '+ Статья' },
    { to: `${hall}?tab=blog`, label: '+ Запись в блог' },
  ].filter(Boolean) as { to: string; label: string }[]
})

// The chosen filter lives in the address (?feed=works), so a filtered feed can be shared
const valid = (v: unknown): Kind => (FILTERS.some((f) => f.id === v) ? (v as Kind) : 'all')
const kind = ref<Kind>(valid(route.query.feed))

interface FeedPage { items: FeedEntry[]; next_before: string | null }
const { data, pending, refresh } = await useAsyncData(
  'feed',
  () => api<FeedPage>('/api/feed', { params: { kind: kind.value, limit: 15 } }),
  { watch: [kind] },
)

// ---- «+ Эскиз»: the recorder opens above the feed; a published sketch appears at once
const sketching = ref(false)
const sketchPanel = ref<{ $el: HTMLElement }>()
async function startSketch() {
  sketching.value = true
  await nextTick()
  sketchPanel.value?.$el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
async function onSketch() {
  extra.value = []
  cursor.value = null
  await refresh()
}
const extra = ref<FeedEntry[]>([])
const cursor = ref<string | null>(null)
const keyOf = (item: FeedEntry) => `${item.type}-${item.opus?.id || item.performance?.id || item.post?.id}`
const removed = reactive(new Set<string>())
const items = computed(() => [...(data.value?.items || []), ...extra.value].filter((item) => !removed.has(keyOf(item))))
const nextBefore = computed(() => (extra.value.length ? cursor.value : data.value?.next_before) || null)
const loadingMore = ref(false)
const loading = computed(() => pending.value || loadingMore.value)

watch(kind, () => {
  extra.value = []
  cursor.value = null
})

function choose(id: Kind) {
  kind.value = id
  router.replace({ query: { ...route.query, feed: id === 'all' ? undefined : id } })
}

// The next page loads a little before the end of the feed is reached
const sentinel = ref<HTMLElement>()
let observer: IntersectionObserver | undefined
onMounted(() => {
  observer = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) more()
  }, { rootMargin: '0px 0px 800px 0px' })
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

// The side columns: loaded together, none of them may break the page
const { data: side } = await useAsyncData('home-side', async () => {
  const [users, opuses, posts] = await Promise.all([
    api<Profile[]>('/api/users').catch(() => [] as Profile[]),
    api<Page<Opus>>('/api/opuses', { params: { limit: 5 } }).catch(() => null),
    api<Page<unknown>>('/api/posts', { params: { limit: 1 } }).catch(() => null),
  ])
  return { users, opuses, posts }
})
const members = computed(() => side.value?.users || [])
const shownMembers = computed(() => members.value.slice(0, 8))
const newOpuses = computed(() => side.value?.opuses?.items || [])
const counts = computed(() => ({ opuses: side.value?.opuses?.total ?? 0, posts: side.value?.posts?.total ?? 0 }))

function activity(m: Profile) {
  const s = m.stats || {}
  if (s.opuses) return `${s.opuses} ${plural(s.opuses, 'сочинение', 'сочинения', 'сочинений')}`
  if (s.articles) return `${s.articles} ${plural(s.articles, 'статья', 'статьи', 'статей')}`
  if (s.performances) return `${s.performances} ${plural(s.performances, 'исполнение', 'исполнения', 'исполнений')}`
  if (s.posts) return `${s.posts} ${plural(s.posts, 'запись', 'записи', 'записей')}`
  return ''
}
</script>
