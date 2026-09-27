<template>
  <!-- Sticky header of the opus page: ▶ || [01:24 / 08:30] ═══●═══ 🔊 Vol [PDF] -->
  <div class="sticky top-16 z-30 -mx-4 border-y border-gold/20 bg-ink-950/90 px-4 py-3 backdrop-blur-md sm:top-20 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
    <div class="flex items-center gap-3 sm:gap-5">
      <PlayButton :opus="opus" size="md" />
      <span class="shrink-0 font-mono text-sm text-parchment-muted">
        {{ formatTime(current ? player.time : 0) }} <span class="text-parchment-faint">/</span> {{ formatTime(current ? player.duration : opus.audio_duration_seconds) }}
      </span>

      <SeekBar v-if="current" class="flex-1" />
      <button
        v-else
        type="button"
        class="h-4 flex-1 cursor-pointer disabled:cursor-default"
        :disabled="opus.audio_type === 'none'"
        aria-label="Начать с этого места"
        @click="startAt($event)"
      >
        <span class="block h-[3px] bg-gold/20" />
      </button>

      <VolumeControl class="hidden md:flex" />

      <a v-if="canDownload && opus.musicxml_url" :href="`/api/opuses/${opus.slug}/musicxml`" class="btn-secondary hidden shrink-0 px-4 py-1.5 text-sm sm:inline-flex" download title="Открыть в MuseScore, Sibelius, Dorico…">XML ↓</a>
      <a v-if="canDownload && opus.score_url" :href="`/api/opuses/${opus.slug}/score`" class="btn-secondary shrink-0 px-4 py-1.5 text-sm" download>PDF ↓</a>
      <span v-else-if="!canDownload && (opus.score_url || opus.musicxml_url)" class="btn-secondary shrink-0 cursor-not-allowed px-4 py-1.5 text-sm opacity-50" :title="SCORE_ACCESS[opus.score_access]">
        {{ opus.score_access === 'paid' ? 'Ноты · донат' : 'Ноты · просмотр' }}
      </span>
    </div>
    <p v-if="opus.audio_type === 'none'" class="mt-1 text-sm italic text-parchment-faint">Записи пока нет — только партитура.</p>
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { Opus } from '~/utils/types'

const props = defineProps<{ opus: Opus; isAuthor: boolean }>()
const player = usePlayer()
const current = computed(() => player.isCurrent(props.opus.slug))
const canDownload = computed(() => props.opus.score_access === 'free' || props.isAuthor)

// Clicking the idle bar starts playback from that point
const startAt = (e: MouseEvent) => {
  const el = e.currentTarget as HTMLElement
  const ratio = (e.clientX - el.getBoundingClientRect().left) / el.clientWidth
  player.play(props.opus, Math.max(0, ratio * (props.opus.audio_duration_seconds || 0)))
}
</script>
