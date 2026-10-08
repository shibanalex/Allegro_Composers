<template>
  <!-- The site's name is in the header: the page starts straight with the feed -->
  <div class="pt-4 sm:pt-8">
    <h1 class="sr-only">Allegro — сообщество композиторов</h1>

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
        <HintBubble v-if="kind !== 'chat'" id="feed" class="mb-5" text="Лента — всё новое на сайте: сочинения, исполнения, статьи, записи участников. Кнопки рядом оставляют в ленте что-то одно, поиск находит по названию, имени и тексту.">
          <SearchBox />
        </HintBubble>
        <!-- phones: one row that scrolls sideways, not three lines of buttons -->
        <nav class="-mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1 [scrollbar-width:none] sm:mx-0 sm:flex-wrap sm:justify-center sm:overflow-visible sm:px-0 xl:hidden" aria-label="Что показывать в ленте">
          <button
            v-for="f in FILTERS"
            :key="f.id"
            type="button"
            class="chip shrink-0 whitespace-nowrap"
            :class="{ active: kind === f.id, 'max-sm:hidden': f.id === 'chat' }"
            :aria-pressed="kind === f.id"
            @click="choose(f.id)"
          >
            {{ f.label }}
          </button>
        </nav>
        <!-- The chat in place of the feed (computers; on a phone it opens from its own button) -->
        <ChatRoom v-if="kind === 'chat'" class="h-[calc(100vh-12rem)] min-h-[26rem]" />
        <template v-else>
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
        </template>
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
          <h2 class="eyebrow mb-4">Новые участники</h2>
          <ul class="space-y-3">
            <li v-for="m in members" :key="m.id">
              <NuxtLink :to="`/@${m.username}`" class="group flex items-center gap-3">
                <UserAvatar :user="m" :size="44" />
                <span class="min-w-0 leading-tight">
                  <span class="block truncate font-display text-lg italic text-parchment transition group-hover:text-gold-light">{{ m.display_name }}</span>
                  <span class="block truncate text-sm text-parchment-faint">{{ ROLES[m.role]?.label }}<template v-if="activity(m)"> · {{ activity(m) }}</template></span>
                </span>
              </NuxtLink>
            </li>
          </ul>
          <NuxtLink to="/members" class="mt-4 inline-block font-caps text-sm font-semibold tracking-[0.15em] text-gold transition hover:text-gold-light">
            Все участники · {{ memberCount }} →
          </NuxtLink>
          <p v-if="!user" class="mt-4 border-t border-gold/10 pt-4 text-sm text-parchment-faint">
            <NuxtLink to="/register" class="link">Открыть свой зал</NuxtLink> — это бесплатно. <NuxtLink to="/about" class="link">О сообществе</NuxtLink>
          </p>
        </section>

      </aside>
    </div>

    <!-- Phones: the chat opens from a button, over the whole screen -->
    <button
      v-if="kind !== 'chat'"
      type="button"
      class="play-btn fixed right-4 z-30 h-14 w-14 bg-ink-950/90 text-xl shadow-2xl shadow-black backdrop-blur sm:hidden"
      :class="player.track ? 'bottom-24' : 'bottom-5'"
      aria-label="Открыть чат"
      @click="chatOpen = true"
    >
      <span aria-hidden="true">❝</span>
    </button>
    <Transition name="drop">
      <div v-if="chatOpen" class="fixed inset-0 z-50 flex flex-col bg-ink-950 sm:hidden">
        <ChatRoom class="min-h-0 flex-1 border-0">
          <template #close>
            <button type="button" class="px-2 text-lg text-parchment-muted transition hover:text-gold" aria-label="Закрыть чат" @click="chatOpen = false">✕</button>
          </template>
        </ChatRoom>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { FeedEntry, Opus, Page, Profile } from '~/utils/types'

definePageMeta({ wide: true })
useSeoMeta({
  title: 'Allegro — сообщество композиторов',
  description: 'Сообщество композиторов, теоретиков и исполнителей: новые сочинения с партитурами и записями, исполнения, статьи и блоги.',
})

type Kind = 'all' | 'works' | 'sketches' | 'feedback' | 'performances' | 'articles' | 'blogs' | 'chat'
const FILTERS: { id: Kind; label: string; icon: string }[] = [
  { id: 'all', label: 'Всё', icon: '✦' },
  { id: 'works', label: 'Сочинения', icon: '♪' },
  { id: 'sketches', label: 'Эскизы', icon: '✐' },
  { id: 'feedback', label: 'Ждут отзыва', icon: '?' },
  { id: 'performances', label: 'Исполнения', icon: '♫' },
  { id: 'articles', label: 'Статьи и обзоры', icon: '§' },
  { id: 'blogs', label: 'Блоги', icon: '✎' },
  { id: 'chat', label: 'Чат', icon: '❝' },
]
const EMPTY: Record<Kind, string> = {
  all: 'В залах пока тихо',
  works: 'Новых сочинений пока нет',
  sketches: 'Эскизов пока нет',
  feedback: 'Сейчас никто не ждёт отзыва',
  performances: 'Исполнений пока нет',
  articles: 'Статей пока нет',
  blogs: 'Записей пока нет',
  chat: '',
}

const api = useApi()
const route = useRoute()
const router = useRouter()
const player = usePlayer()

// Phones: the chat over the whole screen (the page behind it doesn't scroll meanwhile)
const chatOpen = ref(false)
watch(chatOpen, (open) => {
  if (import.meta.client) document.documentElement.style.overflow = open ? 'hidden' : ''
})
onBeforeUnmount(() => {
  if (import.meta.client) document.documentElement.style.overflow = ''
})
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
  () => (kind.value === 'chat'
    ? Promise.resolve<FeedPage>({ items: [], next_before: null }) // the chat loads its own messages
    : api<FeedPage>('/api/feed', { params: { kind: kind.value, limit: 15 } })),
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
  const [users, opuses] = await Promise.all([
    api<Page<Profile>>('/api/users', { params: { limit: 6 } }).catch(() => null),
    api<Page<Opus>>('/api/opuses', { params: { limit: 5 } }).catch(() => null),
  ])
  return { users, opuses }
})
// The newest members; everyone is on /members
const members = computed(() => side.value?.users?.items || [])
const memberCount = computed(() => side.value?.users?.total || 0)
const newOpuses = computed(() => side.value?.opuses?.items || [])

function activity(m: Profile) {
  const s = m.stats || {}
  if (s.opuses) return `${s.opuses} ${plural(s.opuses, 'сочинение', 'сочинения', 'сочинений')}`
  if (s.articles) return `${s.articles} ${plural(s.articles, 'статья', 'статьи', 'статей')}`
  if (s.performances) return `${s.performances} ${plural(s.performances, 'исполнение', 'исполнения', 'исполнений')}`
  if (s.posts) return `${s.posts} ${plural(s.posts, 'запись', 'записи', 'записей')}`
  return ''
}
</script>
