<template>
  <div v-if="opus" class="pt-6">
    <OpusTransport :opus="opus" :is-author="isAuthor" />

    <div class="mt-10 grid gap-12 lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
      <!-- Score: interactive MusicXML with a cursor, or the PDF with page turns.
           The MusicXML column stays on screen while reading critiques, so timecodes are seen landing. -->
      <section :class="{ 'lg:sticky lg:top-[11.5rem] lg:self-start': opus.musicxml_url && view === 'musicxml' }">
        <div v-if="opus.musicxml_url && opus.score_url" class="mb-5 flex gap-2">
          <button type="button" class="chip" :class="{ active: view === 'musicxml' }" @click="view = 'musicxml'">♫ Интерактивная · MusicXML</button>
          <button type="button" class="chip" :class="{ active: view === 'pdf' }" @click="view = 'pdf'">𝄞 PDF</button>
        </div>
        <ClientOnly v-if="opus.musicxml_url && view === 'musicxml'">
          <MusicXmlViewer ref="viewer" :opus="opus" @seek="seek" />
          <template #fallback>
            <div class="frame frame-thin"><div class="frame-inner flex min-h-[24rem] items-center justify-center bg-[#f5efe0] font-elegant text-xl italic text-ink-600">Партитура загружается…</div></div>
          </template>
        </ClientOnly>
        <ClientOnly v-else-if="opus.score_url">
          <ScoreViewer :opus="opus" />
          <template #fallback>
            <div class="frame frame-thin"><div class="frame-inner flex aspect-[1/1.414] items-center justify-center bg-[#f5efe0] font-elegant text-xl italic text-ink-600">Партитура загружается…</div></div>
          </template>
        </ClientOnly>
        <div v-else class="frame">
          <div class="frame-inner aspect-square">
            <MediaImg v-if="opus.cover_url" :src="opus.cover_url" :alt="opus.title" class="h-full w-full object-cover" />
          </div>
          <p class="bg-ink-950 p-4 text-center font-elegant italic text-parchment-faint">Автор ещё не загрузил партитуру</p>
        </div>
      </section>

      <!-- Passport, explication, critiques -->
      <aside class="space-y-12">
        <header>
          <p class="eyebrow">{{ genreLabel(opus.genre) }}</p>
          <h1 class="mt-3 font-caps text-3xl font-semibold uppercase leading-tight tracking-[0.08em] text-parchment sm:text-4xl">{{ opus.title }}</h1>
          <p v-if="opus.subtitle" class="mt-2 font-display text-xl italic text-gold-light">{{ opus.subtitle }}</p>

          <NuxtLink :to="`/@${opus.author.username}`" class="mt-5 flex items-center gap-3 text-parchment transition hover:text-gold-light">
            <UserAvatar :user="opus.author" :size="40" />
            <span>
              <span class="block font-display italic">{{ opus.author.display_name }}</span>
              <span v-if="opus.author.pseudonym" class="block text-sm text-parchment-faint">{{ opus.author.pseudonym }}</span>
            </span>
          </NuxtLink>

          <dl class="mt-6 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 border-y border-gold/15 py-4 text-parchment-muted">
            <template v-if="opus.instruments.length">
              <dt class="field-label mb-0 self-center">Состав</dt>
              <dd class="flex flex-wrap gap-x-1">
                <template v-for="(name, i) in [...new Set(opus.instruments)]" :key="name">
                  <NuxtLink :to="`/search?q=${encodeURIComponent(name)}`" class="transition hover:text-gold-light">{{ instrumentsText(opus.instruments.filter((x) => x === name)) }}</NuxtLink><span v-if="i < new Set(opus.instruments).size - 1">,</span>
                </template>
              </dd>
            </template>
            <template v-if="opus.key_signature"><dt class="field-label mb-0 self-center">Тональность</dt><dd>{{ opus.key_signature }}</dd></template>
            <template v-if="opus.year"><dt class="field-label mb-0 self-center">Год</dt><dd>{{ opus.year }}</dd></template>
            <template v-if="opus.audio_duration_seconds"><dt class="field-label mb-0 self-center">Длительность</dt><dd class="font-mono text-sm">{{ formatTime(opus.audio_duration_seconds) }}</dd></template>
            <template v-if="opus.score_url || opus.musicxml_url">
              <dt class="field-label mb-0 self-center">Партитура</dt>
              <dd>
                <span v-if="opus.musicxml_url">MusicXML</span><span v-if="opus.musicxml_url && opus.score_url"> + </span><span v-if="opus.score_url">PDF, {{ opus.score_page_count }} стр.</span>
                · {{ SCORE_ACCESS[opus.score_access] }}
              </dd>
            </template>
          </dl>

          <!-- Like, share in one's blog -->
          <div class="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-parchment-faint">
            <LikeButton kind="opus" :id="opus.id" :value="likes" />
            <button v-if="opus.status === 'published' && can('publish_note')" type="button" class="inline-flex items-center gap-1.5 transition hover:text-gold-light" @click="sharing = true">
              <span class="text-lg leading-none" aria-hidden="true">↻</span>В свой блог
            </button>
            <ShareButton :path="`/opus/${opus.slug}`" :title="opus.title" />
          </div>
          <ShareDialog v-if="sharing" :opus="opus" @close="sharing = false" @published="(p) => navigateTo(`/posts/${p.slug}`)" />

          <div v-if="isAuthor" class="mt-6 flex flex-wrap gap-3">
            <span v-if="opus.status !== 'published'" class="chip active">{{ STATUSES[opus.status] }}</span>
            <NuxtLink :to="`/create/opus?edit=${opus.slug}`" class="btn-secondary px-4 py-1.5 text-sm">Редактировать</NuxtLink>
            <button class="btn-ghost text-sm hover:text-red-300" @click="remove">Удалить</button>
          </div>
        </header>

        <section v-if="opus.description_md">
          <h2 class="font-caps text-lg font-semibold tracking-[0.2em] text-gold">Экспликация · анализ</h2>
          <MarkdownContent :text="opus.description_md" timecodes variant="compact" class="mt-4" @seek="seek" />
        </section>

        <section v-if="threads.length">
          <h2 class="font-caps text-lg font-semibold tracking-[0.2em] text-gold">Обзоры</h2>
          <ul class="mt-3 space-y-2">
            <li v-for="t in threads" :key="t.id">
              <NuxtLink :to="`/posts/${t.slug}`" class="font-display italic text-parchment transition hover:text-gold-light">«{{ t.title }}»</NuxtLink>
              <span class="text-sm text-parchment-faint"> · {{ t.author.display_name }} · {{ t.comment_count }} {{ plural(t.comment_count, 'комментарий', 'комментария', 'комментариев') }}</span>
            </li>
          </ul>
        </section>

        <section v-if="mentions?.length">
          <h2 class="font-caps text-lg font-semibold tracking-[0.2em] text-gold">Упоминания</h2>
          <div class="mt-3 space-y-3">
            <QuoteCard v-for="m in mentions" :key="m.id" :post="m" />
          </div>
        </section>

        <CommentThread :target="{ opus_id: opus.id }" :opus="opus" :owner-id="opus.author.id" title="Комментарии" @seek="seek" />
      </aside>
    </div>

    <!-- Members' performances of this work -->
    <section v-if="performanceCount || can('publish_performance')" class="mt-20">
      <h2 class="mb-8 text-center font-caps text-lg font-semibold tracking-[0.2em] text-gold">Исполнения</h2>
      <PerformanceList :opus="opus.slug" :opus-id="opus.id" empty-text="Это сочинение ещё никто не исполнил — станьте первым" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { Opus, Page, Post, PostBrief, Reactions } from '~/utils/types'

const route = useRoute()
const api = useApi()
const player = usePlayer()
const { user } = useAuth()
const slug = route.params.slug as string

const { data: opus, error } = await useAsyncData(`opus-${slug}`, () => api<Opus>(`/api/opuses/${slug}`))
if (error.value || !opus.value) throw pageError(error.value, 'Опус не найден')

const { data: threadPage } = await useAsyncData(`opus-threads-${slug}`, () =>
  api<Page<Post>>('/api/posts', { params: { kind: ['article', 'workshop'], opus: slug, limit: 10 } }),
)
const threads = computed(() => threadPage.value?.items || [])
const { can } = useAuth()
const { data: likes } = await useAsyncData(`opus-likes-${slug}`, () =>
  api<Record<string, Reactions>>('/api/reactions/opus', { params: { ids: opus.value!.id } }).then((r) => r[opus.value!.id]).catch(() => null),
)
const { data: mentions } = await useAsyncData(`opus-mentions-${slug}`, () => api<PostBrief[]>(`/api/mentions/opus/${slug}`).catch(() => []))
const sharing = ref(false)
const { data: performancePage } = await useAsyncData(`opus-performances-count-${slug}`, () =>
  api<Page<unknown>>('/api/performances', { params: { opus: slug, limit: 1 } }),
)
const performanceCount = computed(() => performancePage.value?.total || 0)
const isAuthor = computed(() => user.value?.id === opus.value?.author.id)

useSeoMeta({
  title: () => `${opus.value?.title} — ${opus.value?.author.display_name} · Allegro`,
  description: () => [opus.value?.subtitle, stripMarkdown(opus.value?.description_md || '', 140)].filter(Boolean).join('. ')
    || `${opus.value?.title}: партитура и запись на Allegro`,
  ogImage: () => opus.value?.cover_url || undefined,
  ogType: 'music.song',
})

const origin = useSiteOrigin()
useHead({
  script: [computed(() => jsonLd({
    '@context': 'https://schema.org',
    '@type': 'MusicComposition',
    name: opus.value?.title,
    alternateName: opus.value?.subtitle || undefined,
    url: `${origin}/opus/${opus.value?.slug}`,
    dateCreated: opus.value?.year ? String(opus.value.year) : undefined,
    musicalKey: opus.value?.key_signature || undefined,
    description: stripMarkdown(opus.value?.description_md || '', 300) || undefined,
    composer: {
      '@type': 'Person',
      name: opus.value?.author.display_name,
      alternateName: opus.value?.author.pseudonym || undefined,
      url: `${origin}/@${opus.value?.author.username}`,
    },
  }))],
})

const view = ref<'musicxml' | 'pdf'>(opus.value.musicxml_url ? 'musicxml' : 'pdf')

/** Timecode click: jump the recording there; a stretch («01:20–01:45») plays and stops at its end */
function seek(seconds: number, end?: number) {
  if (!opus.value || opus.value.audio_type === 'none') return
  if (end != null) player.playRange(opus.value, seconds, end)
  else player.play(opus.value, seconds)
}

async function remove() {
  if (!opus.value || !confirm(`Удалить «${opus.value.title}» вместе с файлами и комментариями?`)) return
  if (player.isCurrent(opus.value.slug)) player.close()
  await api(`/api/opuses/${opus.value.slug}`, { method: 'DELETE' })
  navigateTo(`/@${opus.value.author.username}`)
}
</script>
