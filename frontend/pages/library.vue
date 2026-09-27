<template>
  <div>
    <PageHeader eyebrow="Каталог партитур" title="Библиотека" subtitle="Сочинения, которые можно послушать, прочитать и сыграть." />

    <div class="grid gap-10 lg:grid-cols-[17rem_minmax(0,1fr)]">
      <!-- Filters -->
      <aside class="space-y-8">
        <form class="relative" @submit.prevent="set({ q: search || undefined })">
          <input v-model="search" class="field pr-10" placeholder="Название, инструмент…" @blur="set({ q: search || undefined })">
          <span class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gold/60">⌕</span>
        </form>

        <FilterGroup title="Состав" :facets="facets?.ensembles" :active="query.ensemble" @pick="(v) => set({ ensemble: v })" />
        <FilterGroup title="Форма" :facets="facets?.forms" :active="query.form" @pick="(v) => set({ form: v })" />

        <div>
          <p class="field-label">Тональность</p>
          <select class="field" :value="query.key || ''" @change="set({ key: ($event.target as HTMLSelectElement).value || undefined })">
            <option value="">Любая</option>
            <option v-for="k in facets?.keys" :key="k.value" :value="k.value">{{ k.label }} ({{ k.count }})</option>
          </select>
        </div>

        <div>
          <p class="field-label">Сложность исполнения</p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="d in facets?.difficulty"
              :key="d.value"
              type="button"
              class="chip gap-2"
              :class="{ active: query.difficulty === d.value }"
              :title="d.label"
              @click="set({ difficulty: query.difficulty === d.value ? undefined : d.value })"
            >
              <DifficultyDots :value="Number(d.value)" />
            </button>
          </div>
        </div>

        <FilterGroup v-if="facets?.tags.length" title="Инструменты и теги" :facets="facets.tags" :active="query.tag" @pick="(v) => set({ tag: v })" />

        <button v-if="hasFilters" type="button" class="link font-caps text-sm font-semibold tracking-[0.15em]" @click="clearAll">Сбросить фильтры</button>
      </aside>

      <!-- Results -->
      <section>
        <div class="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-gold/15 pb-4">
          <p class="font-elegant text-xl italic text-parchment-muted">
            {{ total }} {{ plural(total, 'сочинение', 'сочинения', 'сочинений') }}
          </p>
          <select class="field w-auto py-1.5" :value="query.sort || 'new'" @change="set({ sort: ($event.target as HTMLSelectElement).value })">
            <option value="new">Сначала новые</option>
            <option value="popular">Популярные</option>
            <option value="title">По названию</option>
          </select>
        </div>

        <EmptyState v-if="!pending && !items.length">Под эти условия ничего не подошло</EmptyState>

        <ul class="divide-y divide-gold/10" :class="{ 'opacity-50 transition': pending }">
          <li v-for="o in items" :key="o.id" class="group flex items-center gap-4 py-5 sm:gap-6">
            <PlayButton :opus="o" />
            <NuxtLink :to="`/opus/${o.slug}`" class="frame frame-thin hidden h-16 w-24 shrink-0 sm:block">
              <div class="frame-inner"><img v-if="o.cover_url" :src="o.cover_url" alt="" class="h-full w-full object-cover" loading="lazy"></div>
            </NuxtLink>
            <div class="min-w-0 flex-1">
              <NuxtLink :to="`/opus/${o.slug}`" class="block">
                <h3 class="truncate text-xl transition group-hover:text-gold-light">{{ o.title }}</h3>
                <p class="truncate text-sm italic text-parchment-faint">
                  <span v-if="o.subtitle">{{ o.subtitle }} · </span>{{ o.author.display_name }}
                </p>
              </NuxtLink>
              <div class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-sm text-parchment-muted">
                <span>{{ ENSEMBLES[o.ensemble] }}</span>
                <span>{{ FORMS[o.form] }}</span>
                <span v-if="o.key_signature">{{ o.key_signature }}</span>
                <DifficultyDots v-if="o.difficulty" :value="o.difficulty" />
              </div>
            </div>
            <div class="hidden shrink-0 text-right text-sm text-parchment-faint md:block">
              <p v-if="o.audio_duration_seconds" class="font-mono">{{ formatTime(o.audio_duration_seconds) }}</p>
              <p v-if="o.musicxml_url">♫ MusicXML</p>
              <p v-else-if="o.score_url">𝄞 {{ o.score_page_count }} стр.</p>
            </div>
          </li>
        </ul>

        <div v-if="items.length < total" class="mt-10 text-center">
          <button class="btn-secondary" :disabled="pending" @click="more">Показать ещё</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Facets, Opus, Page } from '~/utils/types'

useSeoMeta({ title: 'Библиотека — Allegro', description: 'Каталог партитур с фильтрами по составу, форме, тональности и сложности.' })

const api = useApi()
const route = useRoute()
const router = useRouter()

const KEYS = ['ensemble', 'form', 'key', 'difficulty', 'tag', 'q', 'sort'] as const
const query = computed(() => Object.fromEntries(KEYS.map((k) => [k, route.query[k] as string | undefined])) as Record<(typeof KEYS)[number], string | undefined>)
const hasFilters = computed(() => KEYS.some((k) => k !== 'sort' && query.value[k]))
const search = ref(query.value.q || '')

const set = (patch: Record<string, string | undefined>) => router.replace({ query: { ...route.query, ...patch } })
const clearAll = () => {
  search.value = ''
  router.replace({ query: {} })
}

const { data: facets } = await useAsyncData('facets', () => api<Facets>('/api/library/facets'))

const limit = ref(20)
const { data, pending } = await useAsyncData(
  'library',
  () => api<Page<Opus>>('/api/opuses', { params: { ...query.value, limit: limit.value } }),
  { watch: [query, limit] },
)
const items = computed(() => data.value?.items || [])
const total = computed(() => data.value?.total || 0)
const more = () => (limit.value += 20)

watch(() => route.query.q, (q) => (search.value = (q as string) || ''))
</script>
