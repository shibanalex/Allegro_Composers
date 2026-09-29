<template>
  <!-- A post on its own page: the same card as in the feed, opened — author on top, the post, actions under
       it, the discussion below; one column of one width, like a post in any social network -->
  <div v-if="post" class="mx-auto w-full max-w-2xl pb-16 pt-6 sm:pt-10">
    <NuxtLink
      :to="post.kind === 'note' || post.kind === 'sketch' ? `/@${post.author.username}?tab=blog` : '/'"
      class="mb-5 inline-flex items-center gap-2 font-caps text-sm font-semibold tracking-[0.15em] text-parchment-faint transition hover:text-gold-light"
    >
      ← {{ post.kind === 'note' || post.kind === 'sketch' ? `Блог · ${post.author.display_name}` : 'Лента' }}
    </NuxtLink>

    <FeedItem :item="entry" detail @removed="navigateTo(`/@${post.author.username}`)" />

    <!-- Posts whose text links here -->
    <section v-if="mentions?.length" class="mt-10">
      <h2 class="eyebrow mb-4">Ссылаются на эту запись</h2>
      <div class="space-y-3">
        <QuoteCard v-for="m in mentions" :key="m.id" :post="m" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { FeedEntry, Post, PostBrief } from '~/utils/types'

const route = useRoute()
const api = useApi()
const slug = route.params.slug as string

// One request: the post comes with its likes; mentions and comments fill in after the page is shown
const { data: post, error } = await useAsyncData(`post-${slug}`, () => api<Post & { likes?: FeedEntry['likes'] }>(`/api/posts/${slug}`))
if (error.value || !post.value) throw createError({ statusCode: 404, statusMessage: 'Публикация не найдена', fatal: true })
const { data: mentions } = useLazyAsyncData(`post-mentions-${slug}`, () => api<PostBrief[]>(`/api/mentions/post/${slug}`).catch(() => []), { server: false })

const entry = computed<FeedEntry>(() => ({
  type: 'post', created_at: post.value!.created_at, post: post.value!, likes: post.value!.likes || { count: 0, mine: false },
}))

// Blog posts may be untitled, like channel messages
const heading = computed(() => post.value?.title || `Запись от ${formatDate(post.value?.created_at)}`)
useSeoMeta({
  title: () => `${heading.value} — Allegro`,
  description: () => post.value?.excerpt || stripMarkdown(post.value?.content_md || '', 160),
  ogImage: () => post.value?.cover_url || undefined,
})
</script>
