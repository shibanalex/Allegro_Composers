<template>
  <!-- One entry of the main feed: who published it, when, from which hall — then the thing itself -->
  <article class="card !p-0">
    <header class="flex items-center gap-4 px-5 pt-5 sm:px-8 sm:pt-7">
      <NuxtLink :to="`/@${author.username}`" class="shrink-0"><UserAvatar :user="author" :size="48" /></NuxtLink>
      <div class="min-w-0 flex-1 leading-tight">
        <NuxtLink :to="`/@${author.username}`" class="font-display text-xl italic text-parchment transition hover:text-gold-light">{{ author.display_name }}</NuxtLink>
        <p class="truncate text-sm text-parchment-faint">
          {{ action }} · <time :datetime="item.created_at">{{ when }}</time>
        </p>
      </div>
      <span class="hidden font-caps text-xs font-semibold tracking-[0.15em] text-gold/70 sm:block">{{ ROLES[author.role || 'listener']?.label }}</span>
    </header>

    <div class="px-5 pb-6 pt-5 sm:px-8 sm:pb-8">
      <!-- A new work -->
      <template v-if="item.opus">
        <div class="group flex gap-5">
          <NuxtLink :to="`/opus/${item.opus.slug}`" class="frame frame-thin hidden h-44 w-44 shrink-0 sm:block">
            <div class="frame-inner">
              <MediaImg v-if="item.opus.cover_url" :src="item.opus.cover_url" alt="" class="h-full w-full object-cover" loading="lazy" />
              <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-ink-700 to-ink-900">
                <span class="font-display text-7xl italic text-gold/25">{{ item.opus.title.charAt(0) }}</span>
              </div>
            </div>
          </NuxtLink>
          <div class="min-w-0 flex-1">
            <NuxtLink :to="`/opus/${item.opus.slug}`" class="block">
              <h3 class="text-3xl leading-tight transition group-hover:text-gold-light">{{ item.opus.title }}</h3>
              <p v-if="item.opus.subtitle" class="font-elegant text-lg italic text-parchment-muted">{{ item.opus.subtitle }}</p>
            </NuxtLink>
            <p class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-parchment-faint">
              <span>{{ genreLabel(item.opus.genre) }}</span>
              <span v-if="item.opus.instruments.length">{{ instrumentsText(item.opus.instruments) }}</span>
              <span v-if="item.opus.key_signature">{{ item.opus.key_signature }}</span>
              <span v-if="item.opus.musicxml_url">♫ ноты с курсором</span>
              <span v-else-if="item.opus.score_url">𝄞 партитура</span>
              <span v-if="item.opus.audio_duration_seconds" class="font-mono">{{ formatTime(item.opus.audio_duration_seconds) }}</span>
            </p>
            <div class="mt-5 flex items-center gap-4">
              <PlayButton v-if="item.opus.audio_type !== 'none'" :opus="item.opus" />
              <NuxtLink :to="`/opus/${item.opus.slug}`" class="font-caps text-sm font-semibold tracking-[0.15em] text-gold transition hover:text-gold-light">Открыть ноты →</NuxtLink>
            </div>
          </div>
        </div>
      </template>

      <!-- A performance -->
      <PerformanceCard v-else-if="item.performance" :performance="item.performance" bare />

      <!-- An article, a review, the site's news -->
      <NuxtLink v-else-if="item.post && item.post.kind !== 'note'" :to="`/posts/${item.post.slug}`" class="group flex gap-5">
        <div class="min-w-0 flex-1">
          <p class="eyebrow text-xs">{{ POST_KINDS[item.post.kind] }}<template v-if="item.post.opus"> · об опусе «{{ item.post.opus.title }}»</template></p>
          <h3 class="mt-1 text-3xl leading-tight transition group-hover:text-gold-light">{{ item.post.title }}</h3>
          <p class="mt-2 line-clamp-3 font-elegant text-lg italic text-parchment-muted [overflow-wrap:anywhere]">{{ item.post.excerpt || stripMarkdown(item.post.content_md, 260) }}</p>
          <span class="mt-2 inline-block font-caps text-sm font-semibold tracking-[0.15em] text-gold">Читать →</span>
        </div>
        <div v-if="item.post.cover_url" class="frame frame-thin hidden h-36 w-52 shrink-0 sm:block">
          <div class="frame-inner"><MediaImg :src="item.post.cover_url" alt="" class="h-full w-full object-cover" loading="lazy" /></div>
        </div>
      </NuxtLink>

      <!-- A blog post, like a message in a channel -->
      <template v-else-if="item.post">
        <MarkdownContent v-if="item.post.content_md" :text="item.post.content_md" variant="compact" />
        <ImageGallery v-if="images.length" :images="images" class="mt-4" />
        <div v-for="a in audios" :key="a.url" class="mt-4 border border-gold/20 bg-ink-950/50 p-3">
          <p class="mb-2 truncate text-sm text-parchment-muted">♪ {{ a.name }}</p>
          <audio :src="a.url" controls preload="none" class="w-full" />
        </div>
        <AttachmentList v-if="files.length" :files="files" class="mt-4" />
        <OpusMiniCard v-if="item.post.opus" :opus="item.post.opus" class="mt-4" />
        <QuoteCard v-if="item.post.quote" :post="item.post.quote" class="mt-4" />
      </template>
    </div>

    <!-- Actions: like, discuss right here, quote or share, copy the link -->
    <footer class="border-t border-gold/10 px-5 py-2.5 text-parchment-faint sm:px-8">
      <div class="flex flex-wrap items-center gap-x-6 gap-y-2">
        <LikeButton :kind="item.type" :id="targetId" :value="item.likes" />
        <button v-if="discussion" type="button" class="inline-flex items-center gap-1.5 transition hover:text-gold-light" :aria-expanded="open" @click="open = !open">
          <span class="text-lg leading-none" aria-hidden="true">✎</span>{{ discussion.label }}
        </button>
        <button v-if="shareable && can('publish_note')" type="button" class="inline-flex items-center gap-1.5 transition hover:text-gold-light" @click="sharing = true">
          <span class="text-lg leading-none" aria-hidden="true">↻</span>{{ item.post ? 'Процитировать' : 'Поделиться' }}
        </button>
        <button type="button" class="ml-auto inline-flex items-center gap-1.5 transition hover:text-gold-light" :title="link" @click="copyLink">
          <span aria-hidden="true">🔗</span>{{ copied ? 'Ссылка скопирована' : 'Ссылка' }}
        </button>
      </div>
      <div v-if="open && discussion" class="mt-4 border-t border-gold/10 pt-2">
        <Suspense>
          <CommentThread :target="discussion.target" :opus="item.opus" :owner-id="author.id" :title="discussion.title" />
          <template #fallback><p class="py-4 font-elegant italic text-parchment-faint">Загружаю обсуждение…</p></template>
        </Suspense>
      </div>
    </footer>
    <ShareDialog v-if="sharing" :quote="item.post ? briefOf(item.post) : null" :opus="item.opus" @close="sharing = false" />
  </article>
</template>

<script setup lang="ts">
import type { Attachment, FeedEntry } from '~/utils/types'

const props = defineProps<{ item: FeedEntry }>()
const { can } = useAuth()

const targetId = computed(() => (props.item.opus || props.item.performance || props.item.post)!.id)

// Comments open right under the entry; works have «рецензии», posts — comments; performances aren't discussed
const discussion = computed(() => {
  const { post, opus } = props.item
  if (post) {
    const n = post.comment_count
    return { target: { post_id: post.id }, title: 'Обсуждение', label: n ? `${n} ${plural(n, 'комментарий', 'комментария', 'комментариев')}` : 'Обсудить' }
  }
  if (opus) {
    const n = opus.critique_count
    return { target: { opus_id: opus.id }, title: 'Рецензии', label: n ? `${n} ${plural(n, 'рецензия', 'рецензии', 'рецензий')}` : 'Рецензия' }
  }
  return null
})
const open = ref(false)

// A post can be quoted, a work shared — both become a blog post of one's own
const shareable = computed(() => !!(props.item.opus || (props.item.post && props.item.post.status === 'published')))
const sharing = ref(false)

const link = computed(() => {
  const { post, opus, performance } = props.item
  return post ? `/posts/${post.slug}` : opus ? `/opus/${opus.slug}` : performance?.opus ? `/opus/${performance.opus.slug}` : `/@${author.value.username}`
})
const copied = ref(false)
async function copyLink() {
  try {
    await navigator.clipboard.writeText(new URL(link.value, location.origin).href)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {}
}

const author = computed(() => props.item.opus?.author || props.item.performance?.performer || props.item.post!.author)

const action = computed(() => {
  if (props.item.opus) return 'новое сочинение'
  if (props.item.performance) return 'новое исполнение'
  const kind = props.item.post?.kind
  return kind === 'article' ? (props.item.post?.opus ? 'обзор' : 'статья') : kind === 'news' ? 'новости сообщества' : 'запись в блоге'
})

// «сегодня, 19:40» / «вчера, 08:12» / «12 сентября»
const when = computed(() => {
  const day = formatDate(props.item.created_at)
  const today = formatDate(new Date().toISOString())
  const yesterday = formatDate(new Date(Date.now() - 86_400_000).toISOString())
  if (day === today) return `сегодня, ${formatClock(props.item.created_at)}`
  if (day === yesterday) return `вчера, ${formatClock(props.item.created_at)}`
  return day
})

const isAudio = (a: Attachment) => a.content_type?.startsWith('audio/')
const attachments = computed(() => props.item.post?.attachments || [])
const images = computed(() => attachments.value.filter(isImage))
const audios = computed(() => attachments.value.filter(isAudio))
const files = computed(() => attachments.value.filter((a) => !isImage(a) && !isAudio(a)))
</script>
