<template>
  <NuxtLink
    :to="`/posts/${post.slug}`"
    class="group flex flex-col gap-6 transition duration-500"
    :class="featured ? 'md:flex-row' : ''"
  >
    <div class="frame shrink-0 transition duration-500 group-hover:-translate-y-1" :class="featured ? 'md:w-3/5' : ''">
      <div class="frame-inner aspect-[16/10]">
        <img v-if="cover" :src="cover" :alt="post.title" loading="lazy" class="h-full w-full object-cover opacity-90 transition duration-700 group-hover:scale-[1.03] group-hover:opacity-100">
        <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-ink-700 to-ink-900">
          <span class="font-display text-8xl italic text-gold/25">{{ post.title.charAt(0) }}</span>
        </div>
      </div>
    </div>

    <div class="flex flex-1 flex-col px-1" :class="featured ? 'md:justify-center md:pl-6' : ''">
      <p class="eyebrow text-gold/70">{{ POST_KINDS[post.kind] }} · {{ formatDate(post.created_at) }}</p>
      <h3 class="mt-3 transition group-hover:text-gold-light" :class="featured ? 'text-3xl italic sm:text-4xl' : 'text-3xl'">{{ post.title }}</h3>
      <p class="mt-4 line-clamp-3 font-elegant text-xl italic text-parchment-muted">{{ post.excerpt || stripMarkdown(post.content_md) }}</p>

      <div class="mt-auto flex items-center gap-4 pt-5 text-sm text-parchment-faint">
        <span v-if="showAuthor" class="flex items-center gap-2">
          <UserAvatar :user="post.author" :size="22" />{{ post.author.display_name }}
        </span>
        <span v-if="post.comment_count">✎ {{ post.comment_count }}</span>
        <span class="ml-auto font-caps text-base font-semibold tracking-[0.2em] text-gold opacity-0 transition group-hover:opacity-100">Читать →</span>
      </div>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
import type { Post } from '~/utils/types'

const props = withDefaults(defineProps<{ post: Post; featured?: boolean; showAuthor?: boolean }>(), { showAuthor: true })
const cover = computed(() => props.post.cover_url || props.post.attachments.find(isImage)?.url)
</script>
