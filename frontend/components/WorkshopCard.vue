<template>
  <!-- A review request posted to the workshop -->
  <article class="card group relative flex gap-5 transition hover:border-gold/30">
    <UserAvatar :user="post.author" :size="48" class="hidden sm:inline-flex" />
    <div class="min-w-0 flex-1">
      <p class="text-sm text-parchment-faint">
        <NuxtLink :to="`/@${post.author.username}`" class="text-parchment-muted hover:text-gold-light">{{ post.author.display_name }}</NuxtLink>
        просит разбора · {{ formatDate(post.created_at) }}
      </p>
      <NuxtLink :to="`/posts/${post.slug}`" class="mt-2 block">
        <h3 class="text-2xl italic leading-snug transition group-hover:text-gold-light">«{{ post.title }}»</h3>
      </NuxtLink>
      <p class="mt-2 line-clamp-2 font-elegant text-lg italic text-parchment-muted">{{ post.excerpt || stripMarkdown(post.content_md, 160) }}</p>

      <div v-if="post.opus" class="mt-4 flex items-center gap-3 border-l-2 border-gold/40 pl-4">
        <PlayButton :opus="post.opus" size="sm" />
        <NuxtLink :to="`/opus/${post.opus.slug}`" class="min-w-0 truncate font-display italic text-parchment transition hover:text-gold-light">
          {{ post.opus.title }}<span v-if="post.opus.subtitle" class="text-parchment-faint"> · {{ post.opus.subtitle }}</span>
        </NuxtLink>
      </div>
    </div>
    <NuxtLink :to="`/posts/${post.slug}`" class="shrink-0 self-start text-center text-parchment-faint transition hover:text-gold-light">
      <span class="block font-display text-3xl text-gold-light">{{ post.comment_count }}</span>
      <span class="font-caps text-xs font-semibold tracking-[0.15em]">{{ plural(post.comment_count, 'ответ', 'ответа', 'ответов') }}</span>
    </NuxtLink>
  </article>
</template>

<script setup lang="ts">
import type { Post } from '~/utils/types'

defineProps<{ post: Post }>()
</script>
