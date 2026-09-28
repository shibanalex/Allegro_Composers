<template>
  <div v-if="post" class="animate-fade-up">
    <header class="mx-auto max-w-3xl pb-10 pt-10 text-center sm:pt-14">
      <p class="eyebrow">{{ POST_KINDS[post.kind] }}</p>
      <NuxtLink v-if="post.kind === 'note'" :to="`/@${post.author.username}?tab=blog`" class="mt-4 inline-block font-caps text-sm font-semibold tracking-[0.2em] text-parchment-faint transition hover:text-gold">← Блог · {{ post.author.display_name }}</NuxtLink>
      <h1 v-if="post.title" class="mt-6 text-4xl italic leading-tight sm:text-6xl">{{ post.title }}</h1>
      <h1 v-else class="mt-6 text-3xl italic leading-tight text-parchment-muted sm:text-4xl">{{ heading }}</h1>
      <Ornament class="mx-auto mt-8 w-64" />
      <p v-if="post.excerpt" class="mx-auto mt-6 max-w-xl font-elegant text-2xl italic text-parchment-muted">{{ post.excerpt }}</p>
      <div class="mt-8 flex flex-wrap items-center justify-center gap-4 font-caps text-base font-semibold tracking-[0.15em] text-parchment-faint">
        <NuxtLink :to="`/@${post.author.username}`" class="flex items-center gap-2 normal-case tracking-normal text-parchment transition hover:text-gold-light">
          <UserAvatar :user="post.author" :size="30" /><span class="font-display italic">{{ post.author.display_name }}</span>
        </NuxtLink>
        <span class="text-gold/50">✦</span>
        <!-- An untitled post already has the date in its heading -->
        <span>{{ post.title ? formatDate(post.created_at) : formatClock(post.created_at) }}</span>
        <span class="text-gold/50">✦</span>
        <span>{{ post.view_count }} {{ plural(post.view_count, 'просмотр', 'просмотра', 'просмотров') }}</span>
      </div>
      <div v-if="isAuthor || can('moderate')" class="mt-6 flex justify-center gap-3">
        <span v-if="post.status !== 'published'" class="chip active">{{ STATUSES[post.status] }}</span>
        <NuxtLink v-if="isAuthor" :to="`/create/post?edit=${post.slug}`" class="btn-secondary px-4 py-1.5 text-sm">Редактировать</NuxtLink>
        <button class="btn-ghost text-sm hover:text-red-300" @click="remove">{{ isAuthor ? 'Удалить' : 'Удалить (модерация)' }}</button>
      </div>
    </header>

    <!-- The piece under discussion, or a work shared in a blog post -->
    <div v-if="post.opus" class="card mx-auto mb-14 flex max-w-prose items-center gap-5">
      <PlayButton :opus="post.opus" size="lg" />
      <div class="min-w-0 flex-1">
        <p class="eyebrow text-xs">{{ post.kind === 'note' ? 'Сочинение' : 'Разбираем опус' }}</p>
        <NuxtLink :to="`/opus/${post.opus.slug}`" class="mt-1 block truncate font-display text-2xl italic transition hover:text-gold-light">{{ post.opus.title }}</NuxtLink>
        <p class="truncate text-sm text-parchment-faint">{{ post.opus.subtitle }} · {{ post.opus.author.display_name }}</p>
        <SeekBar v-if="player.isCurrent(post.opus.slug)" class="mt-2" />
      </div>
    </div>

    <figure v-if="post.cover_url" class="frame mx-auto mb-16 max-w-5xl">
      <div class="frame-inner"><img :src="post.cover_url" :alt="heading" class="max-h-[70vh] w-full object-cover"></div>
    </figure>

    <article class="mx-auto max-w-prose">
      <MarkdownContent :text="post.content_md" :timecodes="!!post.opus" :class="{ dropcap: post.kind === 'article' }" @seek="seek" />
      <QuoteCard v-if="post.quote" :post="post.quote" class="mt-8" />
    </article>

    <!-- Like, quote, copy the link -->
    <div class="mx-auto mt-12 flex max-w-prose flex-wrap items-center gap-x-6 gap-y-2 border-y border-gold/15 py-3 text-parchment-faint">
      <LikeButton kind="post" :id="post.id" :value="likes" />
      <button v-if="post.status === 'published' && can('publish_note')" type="button" class="inline-flex items-center gap-1.5 transition hover:text-gold-light" @click="sharing = true">
        <span class="text-lg leading-none" aria-hidden="true">↻</span>Процитировать
      </button>
      <span class="ml-auto text-sm">{{ post.comment_count }} {{ plural(post.comment_count, 'комментарий', 'комментария', 'комментариев') }}</span>
    </div>
    <ShareDialog v-if="sharing" :quote="briefOf(post)" @close="sharing = false" @published="(p) => navigateTo(`/posts/${p.slug}`)" />

    <!-- Posts whose text links here -->
    <section v-if="mentions?.length" class="mx-auto mt-12 max-w-prose">
      <h2 class="eyebrow mb-4">Ссылаются на эту запись</h2>
      <div class="space-y-3">
        <QuoteCard v-for="m in mentions" :key="m.id" :post="m" />
      </div>
    </section>

    <section v-if="images.length" class="mx-auto mt-16 max-w-4xl">
      <h2 class="eyebrow mb-6 text-center">Изображения</h2>
      <ImageGallery :images="images" />
    </section>
    <section v-if="files.length" class="mx-auto mt-16 max-w-prose">
      <h2 class="eyebrow mb-6 text-center">Материалы</h2>
      <AttachmentList :files="files" />
    </section>

    <div class="mx-auto mt-24 max-w-prose">
      <Ornament class="mx-auto mb-10 w-64" />
      <CommentThread
        :target="{ post_id: post.id }"
        :opus="post.opus"
        :owner-id="post.author.id"
        :title="post.kind === 'workshop' ? 'Разборы' : 'Комментарии'"
        @seek="seek"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { Post, PostBrief, Reactions } from '~/utils/types'

const route = useRoute()
const api = useApi()
const player = usePlayer()
const { user, can } = useAuth()
const slug = route.params.slug as string

const { data: post, error } = await useAsyncData(`post-${slug}`, () => api<Post>(`/api/posts/${slug}`))
if (error.value || !post.value) throw createError({ statusCode: 404, statusMessage: 'Публикация не найдена', fatal: true })

// Blog posts may be untitled, like channel messages
const { data: likes } = await useAsyncData(`post-likes-${slug}`, () =>
  api<Record<string, Reactions>>('/api/reactions/post', { params: { ids: post.value!.id } }).then((r) => r[post.value!.id]).catch(() => null),
)
const { data: mentions } = await useAsyncData(`post-mentions-${slug}`, () => api<PostBrief[]>(`/api/mentions/post/${slug}`).catch(() => []))
const sharing = ref(false)

const heading = computed(() => post.value?.title || `Запись от ${formatDate(post.value?.created_at)}`)
const isAuthor = computed(() => user.value?.id === post.value?.author.id)
const images = computed(() => (post.value?.attachments || []).filter(isImage))
const files = computed(() => (post.value?.attachments || []).filter((a) => !isImage(a)))

useSeoMeta({
  title: () => `${heading.value} — Allegro`,
  description: () => post.value?.excerpt || stripMarkdown(post.value?.content_md || '', 160),
  ogImage: () => post.value?.cover_url || undefined,
})

function seek(seconds: number) {
  if (post.value?.opus) player.play(post.value.opus, seconds)
}

async function remove() {
  if (!post.value || !confirm(`Удалить «${heading.value}»?`)) return
  await api(`/api/posts/${post.value.slug}`, { method: 'DELETE' })
  navigateTo(`/@${post.value.author.username}`)
}
</script>
