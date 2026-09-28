<template>
  <div class="mx-auto max-w-3xl py-10">
    <PageHeader eyebrow="Allegro" title="Поиск" subtitle="По словам в текстах записей, описаниях опусов, названиях и именах." />

    <form class="mb-10 flex items-center gap-3 border-b border-gold/30 pb-2" role="search" @submit.prevent="submit">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" class="shrink-0 text-gold"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
      <input v-model="text" type="search" class="w-full bg-transparent py-2 font-elegant text-2xl italic text-parchment outline-none placeholder:text-parchment-faint/60" placeholder="Например: фортепьянное трио" autofocus>
      <button type="submit" class="btn-secondary shrink-0 px-5 py-1.5 text-sm">Найти</button>
    </form>

    <template v-if="query">
      <p v-if="pending" class="text-center font-elegant text-xl italic text-parchment-faint">Ищем…</p>
      <EmptyState v-else-if="!total">По запросу «{{ query }}» ничего не нашлось</EmptyState>

      <template v-else-if="result">
        <section v-if="result.composers.length" class="mb-12">
          <h2 class="eyebrow mb-4">Композиторы</h2>
          <div class="space-y-3">
            <NuxtLink v-for="c in result.composers" :key="c.username" :to="`/@${c.username}`" class="card flex items-center gap-4 !p-4 transition hover:border-gold/40">
              <UserAvatar :user="c" :size="44" />
              <span class="min-w-0">
                <span class="block font-display text-xl italic"><HighlightText :text="c.display_name" :words="result.words" /></span>
                <span v-if="c.pseudonym || c.bio" class="block truncate text-sm text-parchment-faint">{{ c.pseudonym || c.bio }}</span>
              </span>
            </NuxtLink>
          </div>
        </section>

        <section v-if="result.opuses.length" class="mb-12">
          <h2 class="eyebrow mb-4">Опусы</h2>
          <div class="space-y-3">
            <NuxtLink v-for="o in result.opuses" :key="o.slug" :to="`/opus/${o.slug}`" class="card block !p-5 transition hover:border-gold/40">
              <span class="block font-display text-2xl italic"><HighlightText :text="o.title" :words="result.words" /></span>
              <span class="block text-sm text-parchment-faint">{{ [o.subtitle, o.author.display_name].filter(Boolean).join(' · ') }}</span>
              <span v-if="o.snippet" class="mt-2 block text-parchment-muted"><HighlightText :text="o.snippet" :words="result.words" /></span>
            </NuxtLink>
          </div>
        </section>

        <section v-if="result.posts.length" class="mb-12">
          <h2 class="eyebrow mb-4">Записи и статьи</h2>
          <div class="space-y-3">
            <NuxtLink v-for="p in result.posts" :key="p.slug" :to="`/posts/${p.slug}`" class="card block !p-5 transition hover:border-gold/40">
              <span class="flex flex-wrap items-baseline justify-between gap-2">
                <span class="font-display text-xl italic"><HighlightText :text="p.title || `Запись от ${formatDate(p.created_at)}`" :words="result.words" /></span>
                <span class="text-sm text-parchment-faint">{{ POST_KINDS[p.kind] }} · {{ p.author.display_name }}</span>
              </span>
              <span v-if="p.snippet" class="mt-2 block text-parchment-muted"><HighlightText :text="p.snippet" :words="result.words" /></span>
            </NuxtLink>
          </div>
        </section>

        <section v-if="result.tags.length">
          <h2 class="eyebrow mb-4">Инструменты и теги</h2>
          <div class="flex flex-wrap gap-2">
            <NuxtLink v-for="t in result.tags" :key="t" :to="`/library?tag=${encodeURIComponent(t)}`" class="chip">#{{ t }}</NuxtLink>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { UserBrief } from '~/utils/types'

interface SearchResult {
  composers: (UserBrief & { bio?: string | null })[]
  opuses: { slug: string; title: string; subtitle?: string | null; snippet?: string | null; author: UserBrief }[]
  posts: { slug: string; title: string; kind: keyof typeof POST_KINDS; snippet: string; created_at: string; author: UserBrief }[]
  tags: string[]
  words: string[]
}

const route = useRoute()
const api = useApi()
const query = computed(() => (typeof route.query.q === 'string' ? route.query.q.trim() : ''))
const text = ref(query.value)
watch(query, (q) => (text.value = q))

useSeoMeta({
  title: () => (query.value ? `«${query.value}» — поиск · Allegro` : 'Поиск — Allegro'),
  robots: 'noindex, follow', // result lists are not pages of their own for search engines
})

const { data: result, pending } = await useAsyncData(
  'search',
  () => (query.value ? api<SearchResult>('/api/search', { params: { q: query.value, limit: 50 } }) : Promise.resolve(null)),
  { watch: [query] },
)
const total = computed(() => {
  const r = result.value
  return r ? r.composers.length + r.opuses.length + r.posts.length + r.tags.length : 0
})

function submit() {
  const q = text.value.trim()
  if (q) navigateTo({ path: '/search', query: { q } })
}
</script>
