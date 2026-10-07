<template>
  <!-- Sticky header of the opus page: ▶ || [01:24 / 08:30] ▁▃▆█▅▂ 🔊 Vol [PDF];
       on the waveform a drag selects a stretch, which can be played or commented on -->
  <div class="sticky top-16 z-30 -mx-4 border-y border-gold/20 bg-ink-950/90 px-4 py-3 backdrop-blur-md sm:top-20 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2 sm:flex-nowrap sm:gap-5">
      <PlayButton :opus="opus" size="md" />
      <span class="shrink-0 font-mono text-sm text-parchment-muted">
        {{ formatTime(current ? player.time : 0) }} <span class="text-parchment-faint">/</span> {{ formatTime(current ? player.duration : opus.audio_duration_seconds) }}
      </span>

      <!-- An uploaded recording has a waveform; YouTube, or a waveform not drawn yet, keeps the plain bar -->
      <HintBubble v-if="hasWave" id="wave-select" class="min-w-0 flex-1 max-sm:order-last max-sm:basis-full" text="Это волна записи: клик — перейти к месту, а если протянуть по ней мышью или пальцем — выделится отрезок. Его можно прослушать или прокомментировать.">
        <AudioWave
          :url="opus.audio_url"
          :time="current ? player.time : 0"
          :height="44"
          selectable
          :stretches="commented"
          :selection="selection"
          @seek="onSeek"
          @select="(s) => (selection = s)"
          @stretch="(s) => player.playRange(opus, s.start, s.end)"
        >
          <template #fallback><SeekBar v-if="current" class="mt-4" /><span v-else class="mt-5 block h-[3px] bg-gold/20" /></template>
        </AudioWave>
      </HintBubble>
      <SeekBar v-else-if="current" class="flex-1" />
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

    <!-- The selected stretch: listen, comment, drop -->
    <div v-if="selection" class="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
      <span class="font-mono text-gold-light">{{ formatStretch(selection.start, selection.end) }}</span>
      <button type="button" class="inline-flex items-center gap-1.5 text-parchment-muted transition hover:text-gold-light" @click="player.playRange(opus, selection.start, selection.end)">
        <span aria-hidden="true">▶</span>Прослушать
      </button>
      <button type="button" class="inline-flex items-center gap-1.5 text-parchment-muted transition hover:text-gold-light" @click="commentOn">
        <span aria-hidden="true">✎</span>Комментировать отрезок
      </button>
      <button type="button" class="ml-auto text-parchment-faint transition hover:text-red-300" aria-label="Снять выделение" @click="selection = null">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { Opus } from '~/utils/types'

const props = defineProps<{ opus: Opus; isAuthor: boolean }>()
const player = usePlayer()
const route = useRoute()
const current = computed(() => player.isCurrent(props.opus.slug))
const hasWave = computed(() => props.opus.audio_type === 'hosted_file' && !!props.opus.audio_url)
const { selection, commented } = useStretches(props.opus.id)

/** A click on the waveform: there, in the playing recording, or the recording starts from there */
function onSeek(seconds: number) {
  if (current.value) {
    player.seek(seconds)
    if (!player.playing) player.toggle()
  } else {
    player.play(props.opus, seconds)
  }
}

/** To the comment form below, which takes the selected stretch */
function commentOn() {
  const form = document.getElementById('comment-form')
  if (form) {
    form.scrollIntoView({ behavior: 'smooth', block: 'center' })
    form.querySelector('textarea')?.focus({ preventScroll: true })
  } else {
    navigateTo(`/login?next=${encodeURIComponent(route.fullPath)}`)
  }
}
const canDownload = computed(() => props.opus.score_access === 'free' || props.isAuthor)

// Clicking the idle bar starts playback from that point
const startAt = (e: MouseEvent) => {
  const el = e.currentTarget as HTMLElement
  const ratio = (e.clientX - el.getBoundingClientRect().left) / el.clientWidth
  player.play(props.opus, Math.max(0, ratio * (props.opus.audio_duration_seconds || 0)))
}
</script>
