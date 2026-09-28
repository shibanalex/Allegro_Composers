<template>
  <!-- Compact row of a work: for list views in the hall and the library -->
  <li class="group flex items-center gap-4 py-4 sm:gap-6">
    <span v-if="number" class="hidden w-8 shrink-0 text-right font-display text-xl italic text-gold/60 sm:block">{{ number }}</span>
    <PlayButton :opus="opus" size="sm" />
    <NuxtLink :to="`/opus/${opus.slug}`" class="frame frame-thin hidden h-14 w-14 shrink-0 sm:block">
      <div class="frame-inner"><MediaImg v-if="opus.cover_url" :src="opus.cover_url" alt="" class="h-full w-full object-cover" loading="lazy" /></div>
    </NuxtLink>
    <div class="min-w-0 flex-1">
      <NuxtLink :to="`/opus/${opus.slug}`" class="block">
        <span class="block truncate font-display text-lg transition group-hover:text-gold-light">{{ opus.title }}</span>
        <span class="block truncate text-sm italic text-parchment-faint">
          <template v-if="opus.subtitle">{{ opus.subtitle }} · </template>{{ genreLabel(opus.genre) }}<template v-if="opus.instruments.length"> ({{ instrumentsText(opus.instruments) }})</template><template v-if="opus.key_signature"> · {{ opus.key_signature }}</template><template v-if="opus.year"> · {{ opus.year }}</template>
        </span>
      </NuxtLink>
    </div>
    <span v-if="opus.status !== 'published'" class="chip active shrink-0">{{ STATUSES[opus.status] }}</span>
    <span class="hidden w-14 shrink-0 text-right font-mono text-sm text-parchment-faint md:block">{{ opus.audio_duration_seconds ? formatTime(opus.audio_duration_seconds) : '' }}</span>
    <span class="hidden w-20 shrink-0 text-right text-sm text-parchment-faint lg:block">
      {{ opus.musicxml_url ? '♫ XML' : opus.score_url ? '𝄞 PDF' : '' }}
    </span>
  </li>
</template>

<script setup lang="ts">
import type { Opus } from '~/utils/types'

defineProps<{ opus: Opus; number?: string }>()
</script>
