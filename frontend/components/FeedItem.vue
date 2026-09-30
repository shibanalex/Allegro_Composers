<template>
  <!-- One entry of the main feed: who published it, when, from which hall — then the thing itself.
       The whole card opens the post or work; links, buttons and players inside keep their own clicks. -->
  <article ref="root" class="card !p-0" :class="{ 'feed-entry': !detail }" @click="openEntry">
    <header class="flex items-center gap-4 px-5 pt-5 sm:px-8 sm:pt-7">
      <NuxtLink :to="`/@${author.username}`" class="shrink-0"><UserAvatar :user="author" :size="48" /></NuxtLink>
      <div class="min-w-0 flex-1 leading-tight">
        <NuxtLink :to="`/@${author.username}`" class="font-display text-xl italic text-parchment transition hover:text-gold-light">{{ author.display_name }}</NuxtLink>
        <p class="flex flex-wrap items-center gap-x-2 text-sm text-parchment-faint">
          <span>{{ action }} · <time :datetime="item.created_at">{{ when }}</time><template v-if="detail && item.post"> · {{ item.post.view_count }} {{ plural(item.post.view_count, 'просмотр', 'просмотра', 'просмотров') }}</template></span>
          <span v-if="item.post?.seeking_feedback" class="border border-gold/50 bg-gold/10 px-2 font-caps text-xs font-semibold tracking-[0.12em] text-gold-light">Ищет отзыв</span>
        </p>
      </div>
      <span class="hidden font-caps text-xs font-semibold tracking-[0.15em] text-gold/70 sm:block">{{ ROLES[author.role || 'listener']?.label }}</span>
      <!-- The author's own entry: edit, delete (a moderator may delete a post) -->
      <div v-if="editLink || canDelete" ref="menuRoot" class="relative">
        <button type="button" class="px-2 text-2xl leading-none text-parchment-faint transition hover:text-gold-light" aria-label="Действия" :aria-expanded="menu" @click="menu = !menu">⋯</button>
        <div v-if="menu" class="absolute right-0 top-full z-30 mt-1 w-44 border border-gold/25 bg-ink-900/95 py-1 shadow-2xl shadow-black backdrop-blur">
          <button v-if="mine && item.post?.kind === 'sketch'" type="button" class="block w-full px-4 py-2 text-left font-elegant text-lg text-parchment transition hover:bg-gold/10 hover:text-gold-light" @click="toggleFeedback">
            {{ item.post.seeking_feedback ? 'Отзывов достаточно' : 'Ищу отзыв' }}
          </button>
          <NuxtLink v-if="editLink" :to="editLink" class="block px-4 py-2 font-elegant text-lg text-parchment transition hover:bg-gold/10 hover:text-gold-light">Изменить</NuxtLink>
          <button v-if="canDelete" type="button" class="block w-full px-4 py-2 text-left font-elegant text-lg text-parchment transition hover:bg-gold/10 hover:text-red-300" @click="remove">Удалить</button>
        </div>
      </div>
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

      <!-- A sketch: a short title, one recording, a line of text -->
      <template v-else-if="item.post && item.post.kind === 'sketch'">
        <NuxtLink :to="`/posts/${item.post.slug}`" class="font-display text-2xl leading-tight text-parchment transition hover:text-gold-light">{{ item.post.title }}</NuxtLink>
        <audio v-for="a in audios" :key="a.url" :src="a.url" controls preload="metadata" class="mt-3 w-full" />
        <p v-if="item.post.content_md" class="mt-3 font-elegant text-lg italic text-parchment-muted [overflow-wrap:anywhere]">{{ item.post.content_md }}</p>
      </template>

      <!-- On its own page: an article, a review or news in full -->
      <template v-else-if="detail && item.post && item.post.kind !== 'note'">
        <p class="eyebrow text-xs">{{ POST_KINDS[item.post.kind] }}<template v-if="item.post.opus"> · об опусе «{{ item.post.opus.title }}»</template></p>
        <h1 class="mt-2 text-4xl leading-tight sm:text-5xl">{{ item.post.title }}</h1>
        <p v-if="item.post.excerpt" class="mt-3 font-elegant text-xl italic text-parchment-muted">{{ item.post.excerpt }}</p>
        <div v-if="item.post.cover_url" class="mt-6 border border-gold/20 bg-ink-950 p-2">
          <MediaImg :src="item.post.cover_url" alt="" full class="mx-auto max-h-[28rem] w-auto max-w-full object-contain" />
        </div>
        <OpusMiniCard v-if="item.post.opus" :opus="item.post.opus" class="mt-6" />
        <MarkdownContent :text="item.post.content_md" :timecodes="!!item.post.opus" class="mt-6" :class="{ dropcap: item.post.kind === 'article' }" @seek="seek" />
        <ImageGallery v-if="images.length" :images="images" class="mt-6" />
        <div v-for="a in audios" :key="a.url" class="mt-4 border border-gold/20 bg-ink-950/50 p-3">
          <p class="mb-2 truncate text-sm text-parchment-muted">♪ {{ a.name }}</p>
          <audio :src="a.url" controls preload="none" class="w-full" />
        </div>
        <AttachmentList v-if="files.length" :files="files" class="mt-6" />
        <QuoteCard v-if="item.post.quote" :post="item.post.quote" class="mt-6" />
      </template>

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
        <!-- A long post is folded: «Развернуть» shows it all -->
        <div v-if="item.post.content_md" ref="textBox" class="relative" :class="{ 'max-h-[20rem] overflow-hidden': long && !expanded }">
          <MarkdownContent :text="item.post.content_md" :variant="detail ? undefined : 'compact'" :timecodes="!!item.post.opus" @seek="seek" />
          <div v-if="long && !expanded" class="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-ink-850 to-transparent" />
        </div>
        <button v-if="long && !detail" type="button" class="mt-2 font-caps text-sm font-semibold tracking-[0.15em] text-gold transition hover:text-gold-light" @click="expanded = !expanded">
          {{ expanded ? 'Свернуть ↑' : 'Развернуть ↓' }}
        </button>
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

    <!-- The last comments (from the cache) until the whole discussion is opened -->
    <div v-if="item.comments?.length && !open && !detail" class="space-y-3 border-t border-gold/10 px-5 py-4 sm:px-8">
      <div v-for="c in item.comments" :key="c.id" class="flex gap-3">
        <NuxtLink :to="`/@${c.author.username}`" class="shrink-0"><UserAvatar :user="c.author" :size="30" /></NuxtLink>
        <p class="line-clamp-2 min-w-0 flex-1 text-parchment-muted [overflow-wrap:anywhere]">
          <NuxtLink :to="`/@${c.author.username}`" class="font-display italic text-parchment transition hover:text-gold-light">{{ c.author.display_name }}</NuxtLink>
          {{ stripMarkdown(c.content_md, 220) }}
        </p>
      </div>
    </div>

    <!-- Actions: like, discuss right here, quote or share, copy the link -->
    <footer class="border-t border-gold/10 px-5 py-2.5 text-parchment-faint sm:px-8">
      <div class="flex flex-wrap items-center gap-x-6 gap-y-2">
        <LikeButton :kind="item.type" :id="targetId" :value="item.likes" />
        <button v-if="discussion" type="button" class="inline-flex items-center gap-1.5 transition hover:text-gold-light" :aria-expanded="open" @click="discuss">
          <span class="text-lg leading-none" aria-hidden="true">✎</span>{{ discussion.label }}
        </button>
        <button v-if="shareable && can('publish_note')" type="button" class="inline-flex items-center gap-1.5 transition hover:text-gold-light" @click="sharing = true">
          <span class="text-lg leading-none" aria-hidden="true">↻</span>{{ item.post ? 'Процитировать' : 'В свой блог' }}
        </button>
        <ShareButton class="ml-auto" :path="link" :title="item.post?.title || item.opus?.title || item.performance?.title" />
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
import { usePlayer } from '~/stores/player'
import type { Attachment, FeedEntry } from '~/utils/types'

/** detail: the post on its own page — nothing folded, the discussion open, the card doesn't lead anywhere */
const props = defineProps<{ item: FeedEntry; detail?: boolean }>()
const emit = defineEmits<{ removed: [] }>()
const { user, can } = useAuth()
const api = useApi()

// ---- the card as a whole: a click on its empty parts opens the post or work
function openEntry(e: MouseEvent) {
  if (props.detail) return
  const target = e.target as HTMLElement
  if (target.closest('a, button, input, textarea, select, label, audio, video, [role="dialog"], .no-open')) return
  if (window.getSelection()?.toString()) return // selecting text is not a click
  navigateTo(link.value)
}

// ---- a long blog post is folded
const textBox = ref<HTMLElement>()
const long = ref(false)
const expanded = ref(false)
onMounted(() => {
  if (!props.detail && textBox.value && textBox.value.scrollHeight > 380) long.value = true
})

// A timecode in the text plays the work the post is about
const player = usePlayer()
function seek(seconds: number) {
  if (props.item.post?.opus && props.item.post.opus.audio_type !== 'none') player.play(props.item.post.opus, seconds)
}

// ---- the author's menu
const menu = ref(false)
const menuRoot = ref<HTMLElement>()
const mine = computed(() => !!user.value && user.value.id === author.value.id)
const editLink = computed(() => {
  if (!mine.value) return null
  const { post, opus, performance } = props.item
  if (post) return `/create/post?edit=${post.slug}`
  if (opus) return `/create/opus?edit=${opus.slug}`
  if (performance) return `/@${user.value!.username}?tab=performances`
  return null
})
const canDelete = computed(() => mine.value || (!!props.item.post && can('moderate')))
async function remove() {
  menu.value = false
  const { post, opus, performance } = props.item
  const what = post ? (post.title ? `«${post.title}»` : 'эту запись') : opus ? `«${opus.title}» вместе с файлами` : 'это исполнение'
  if (!confirm(`Удалить ${what}?`)) return
  try {
    if (post) await api(`/api/posts/${post.slug}`, { method: 'DELETE' })
    else if (opus) await api(`/api/opuses/${opus.slug}`, { method: 'DELETE' })
    else if (performance) await api(`/api/performances/${performance.id}`, { method: 'DELETE' })
    emit('removed')
  } catch (e) {
    alert(apiError(e))
  }
}
async function toggleFeedback() {
  menu.value = false
  const post = props.item.post!
  const saved = await api<{ seeking_feedback: boolean }>(`/api/posts/${post.slug}`, { method: 'PATCH', body: { seeking_feedback: !post.seeking_feedback } })
  post.seeking_feedback = saved.seeking_feedback
}
const onDocClick = (e: MouseEvent) => {
  if (menuRoot.value && !menuRoot.value.contains(e.target as Node)) menu.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))

const targetId = computed(() => (props.item.opus || props.item.performance || props.item.post)!.id)

// Comments open right under the entry (works and posts; performances aren't discussed)
const discussion = computed(() => {
  const { post, opus } = props.item
  const n = post ? post.comment_count : opus ? opus.critique_count : 0
  const label = n ? `${n} ${plural(n, 'комментарий', 'комментария', 'комментариев')}` : post?.seeking_feedback ? 'Оставить отзыв' : 'Обсудить'
  if (post) return { target: { post_id: post.id }, title: 'Комментарии', label }
  if (opus) return { target: { opus_id: opus.id }, title: 'Комментарии', label }
  return null
})
const open = ref(!!props.detail)
const root = ref<HTMLElement>()
// In the feed the button opens the discussion under the entry; on the post's page it leads to the field
function discuss() {
  if (!props.detail) return (open.value = !open.value)
  const field = root.value?.querySelector('textarea')
  field?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  field?.focus({ preventScroll: true })
}

// A post can be quoted, a work shared — both become a blog post of one's own
const shareable = computed(() => !!(props.item.opus || (props.item.post && props.item.post.status === 'published')))
const sharing = ref(false)

const link = computed(() => {
  const { post, opus, performance } = props.item
  return post ? `/posts/${post.slug}` : opus ? `/opus/${opus.slug}` : performance?.opus ? `/opus/${performance.opus.slug}` : `/@${author.value.username}`
})

const author = computed(() => props.item.opus?.author || props.item.performance?.performer || props.item.post!.author)

const action = computed(() => {
  if (props.item.opus) return 'новое сочинение'
  if (props.item.performance) return 'новое исполнение'
  const kind = props.item.post?.kind
  if (kind === 'sketch') return 'эскиз'
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
