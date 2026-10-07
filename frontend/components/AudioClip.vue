<template>
  <!-- A sketch or an audio file in a post: ▶ and its waveform (wavesurfer.js), in the site's gold.
       Plays on its own (not through the site player); one at a time. -->
  <div v-if="failed" class="w-full">
    <audio :src="src" controls preload="none" class="w-full" />
  </div>
  <div v-else class="flex w-full items-center gap-3 border border-gold/15 bg-ink-950/50 px-3 py-2" @click.stop>
    <button type="button" class="play-btn h-10 w-10 shrink-0" :aria-label="playing ? 'Пауза' : 'Слушать'" :disabled="!ready" @click="toggle">
      <PlayIcon :playing="playing" :loading="!ready" />
    </button>
    <div ref="host" class="min-w-0 flex-1" :style="{ height: `${height}px` }" />
    <span class="shrink-0 font-mono text-xs text-parchment-muted">{{ formatTime(time) }}<span class="hidden sm:inline"> / {{ formatTime(duration) }}</span></span>
  </div>
</template>

<script setup lang="ts">
import type WaveSurfer from 'wavesurfer.js'
import { usePlayer } from '~/stores/player'

const props = withDefaults(defineProps<{ src: string; height?: number }>(), { height: 40 })

const host = ref<HTMLElement>()
const ready = ref(false)
const failed = ref(false)
const playing = ref(false)
const time = ref(0)
const duration = ref(0)
const player = usePlayer()
let ws: WaveSurfer | null = null

// Only one recording sounds at a time: a clip pauses the one before it and the site player
const sounding = useState<string | null>('clip-sounding', () => null)
const id = useId()

onMounted(async () => {
  const data = await loadPeaks(props.src)
  if (!data) return void (failed.value = true) // the waveform isn't drawn (yet): the browser's own player
  const { default: WaveSurferClass } = await import('wavesurfer.js')
  if (!host.value) return
  duration.value = data.duration
  ws = WaveSurferClass.create({
    container: host.value,
    url: props.src,
    peaks: [data.peaks],
    duration: data.duration,
    height: props.height,
    normalize: true,
    barWidth: 2,
    barGap: 1,
    barRadius: 2,
    cursorWidth: 1,
    waveColor: themeColour('gold', 0.32),
    progressColor: themeColour('gold-light', 0.95),
    cursorColor: themeColour('gold-pale', 0.9),
    hideScrollbar: true,
  })
  ws.getMediaElement().preload = 'none' // nothing is downloaded until it is played
  ws.on('ready', () => (ready.value = true))
  ws.on('timeupdate', (t) => (time.value = t))
  ws.on('play', () => {
    playing.value = true
    sounding.value = id
    if (player.playing) player.pause()
  })
  ws.on('pause', () => (playing.value = false))
  ws.on('finish', () => (playing.value = false))
  ws.on('interaction', () => ws?.play()) // a click on the waveform plays from there
  ws.on('error', () => (failed.value = true))
})

watch(sounding, (who) => {
  if (who !== id && playing.value) ws?.pause()
})
watch(() => player.playing, (now) => {
  if (now && playing.value) ws?.pause()
})

const toggle = () => ws?.playPause()

onBeforeUnmount(() => {
  ws?.destroy()
  ws = null
})
</script>
