<template>
  <!-- A quoted or mentioned post, shown inside another one -->
  <NuxtLink :to="`/posts/${post.slug}`" class="group flex gap-4 border-l-2 border-gold/50 bg-ink-950/40 p-4 transition hover:border-gold hover:bg-ink-950/60">
    <div class="min-w-0 flex-1">
      <p class="flex items-center gap-2 text-sm text-parchment-faint">
        <UserAvatar :user="post.author" :size="22" />
        <span class="font-display italic text-parchment-muted">{{ post.author.display_name }}</span>
        <span>· {{ formatDate(post.created_at) }}</span>
      </p>
      <p v-if="post.title" class="mt-2 font-display text-lg leading-snug text-parchment transition group-hover:text-gold-light">{{ post.title }}</p>
      <p v-if="post.preview" class="mt-1 line-clamp-3 text-parchment-muted [overflow-wrap:anywhere]">{{ post.preview }}</p>
    </div>
    <div v-if="post.image_url" class="frame frame-thin hidden h-20 w-20 shrink-0 sm:block">
      <div class="frame-inner"><MediaImg :src="post.image_url" alt="" class="h-full w-full object-cover" loading="lazy" /></div>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
import type { PostBrief } from '~/utils/types'

defineProps<{ post: PostBrief }>()
</script>
