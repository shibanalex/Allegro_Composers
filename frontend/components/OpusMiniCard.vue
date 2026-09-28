<template>
  <!-- A work shared in a post: cover, title, composer and a play button -->
  <div class="group flex items-center gap-4 border border-gold/20 bg-ink-950/40 p-3">
    <NuxtLink :to="`/opus/${opus.slug}`" class="frame frame-thin h-16 w-16 shrink-0">
      <div class="frame-inner">
        <MediaImg v-if="opus.cover_url" :src="opus.cover_url" alt="" class="h-full w-full object-cover" loading="lazy" />
        <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-ink-700 to-ink-900 font-display text-2xl italic text-gold/30">{{ opus.title.charAt(0) }}</div>
      </div>
    </NuxtLink>
    <NuxtLink :to="`/opus/${opus.slug}`" class="min-w-0 flex-1 leading-tight">
      <span class="block truncate font-display text-lg text-parchment transition group-hover:text-gold-light">{{ opus.title }}</span>
      <span class="block truncate text-sm text-parchment-faint">{{ opus.subtitle ? `${opus.subtitle} · ` : '' }}{{ opus.author.display_name }}</span>
    </NuxtLink>
    <PlayButton v-if="opus.audio_type !== 'none'" :opus="opus" size="sm" />
  </div>
</template>

<script setup lang="ts">
import type { OpusBrief } from '~/utils/types'

defineProps<{ opus: OpusBrief }>()
</script>
