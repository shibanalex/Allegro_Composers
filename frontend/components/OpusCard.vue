<template>
  <!-- Feed card with a built-in mini player -->
  <article class="group">
    <NuxtLink :to="`/opus/${opus.slug}`" class="frame block transition duration-500 group-hover:-translate-y-1">
      <div class="frame-inner aspect-[16/10]">
        <img v-if="opus.cover_url" :src="opus.cover_url" :alt="opus.title" loading="lazy" class="h-full w-full object-cover opacity-90 transition duration-700 group-hover:scale-[1.03] group-hover:opacity-100">
        <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-ink-700 to-ink-900">
          <span class="font-display text-7xl italic text-gold/25">{{ opus.title.charAt(0) }}</span>
        </div>
        <span class="absolute left-3 top-3 z-10 border border-gold/40 bg-ink-950/70 px-2 py-0.5 font-caps text-xs font-semibold tracking-[0.15em] text-gold-light">
          {{ ENSEMBLES[opus.ensemble] }}
        </span>
        <span v-if="opus.status !== 'published'" class="absolute right-3 top-3 z-10 bg-wine/90 px-2 py-0.5 font-caps text-xs font-semibold tracking-[0.15em] text-parchment">
          {{ STATUSES[opus.status] }}
        </span>
      </div>
    </NuxtLink>

    <div class="mt-5 flex items-start gap-4">
      <PlayButton :opus="opus" />
      <div class="min-w-0 flex-1">
        <NuxtLink :to="`/opus/${opus.slug}`" class="block">
          <h3 class="text-2xl leading-tight transition group-hover:text-gold-light">{{ opus.title }}</h3>
          <p v-if="opus.subtitle" class="mt-0.5 font-elegant text-lg italic text-parchment-muted">{{ opus.subtitle }}</p>
        </NuxtLink>
        <NuxtLink v-if="showAuthor" :to="`/@${opus.author.username}`" class="mt-2 inline-flex items-center gap-2 text-parchment-muted transition hover:text-gold-light">
          <UserAvatar :user="opus.author" :size="22" />
          <span class="text-sm">{{ opus.author.display_name }}</span>
        </NuxtLink>
      </div>
    </div>

    <!-- Mini progress for the piece that is playing -->
    <div v-if="current" class="mt-3 flex items-center gap-3">
      <SeekBar />
      <span class="shrink-0 font-mono text-xs text-parchment-muted">{{ formatTime(player.time) }}</span>
    </div>

    <div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-parchment-faint">
      <span>{{ FORMS[opus.form] }}</span>
      <span v-if="opus.key_signature">{{ opus.key_signature }}</span>
      <DifficultyDots v-if="opus.difficulty" :value="opus.difficulty" />
      <span v-if="opus.audio_duration_seconds" class="font-mono text-xs">{{ formatTime(opus.audio_duration_seconds) }}</span>
      <span v-if="opus.musicxml_url" title="Интерактивная партитура: курсор следует за записью">♫ MusicXML</span>
      <span v-else-if="opus.score_url" title="Есть партитура">𝄞 PDF</span>
      <span v-if="opus.critique_count" class="ml-auto">✎ {{ opus.critique_count }} {{ plural(opus.critique_count, 'рецензия', 'рецензии', 'рецензий') }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { Opus } from '~/utils/types'

const props = withDefaults(defineProps<{ opus: Opus; showAuthor?: boolean }>(), { showAuthor: true })
const player = usePlayer()
const current = computed(() => player.isCurrent(props.opus.slug))
</script>
