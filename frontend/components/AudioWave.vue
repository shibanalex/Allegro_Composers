<template>
  <!-- The recording's waveform (wavesurfer.js): shows where the player is, a click jumps there,
       a drag along it selects a stretch; stretches of comments are lit on it -->
  <div class="relative" :style="{ height: `${height}px` }">
    <div v-show="ready" ref="host" class="audio-wave h-full" :class="{ selectable }" />
    <slot v-if="!ready" name="fallback" />
  </div>
</template>

<script setup lang="ts">
import type WaveSurfer from 'wavesurfer.js'
import type RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js'

export interface Stretch { id: string; start: number; end: number; label?: string }

const props = withDefaults(defineProps<{
  url?: string | null // the recording's address: its waveform is asked for by it
  time?: number // where the player is now
  height?: number
  selectable?: boolean // a drag selects a stretch
  stretches?: Stretch[] // stretches lit on the waveform (comments)
  selection?: { start: number; end: number } | null
}>(), { url: null, time: 0, height: 48, selectable: false, stretches: () => [], selection: null })

const emit = defineEmits<{
  seek: [seconds: number]
  select: [stretch: { start: number; end: number } | null]
  stretch: [stretch: Stretch] // a lit stretch was clicked
  ready: [duration: number]
}>()

const host = ref<HTMLElement>()
const ready = ref(false)
let ws: WaveSurfer | null = null
let regions: RegionsPlugin | null = null
const SELECTION = 'selection'

async function build() {
  const data = await loadPeaks(props.url)
  if (!data || !host.value) return
  const [{ default: WaveSurferClass }, { default: Regions }] = await Promise.all([
    import('wavesurfer.js'),
    import('wavesurfer.js/dist/plugins/regions.esm.js'),
  ])
  if (!host.value) return // left the page meanwhile
  regions = Regions.create()
  ws = WaveSurferClass.create({
    container: host.value,
    height: props.height,
    peaks: [data.peaks],
    duration: data.duration,
    normalize: true,
    barWidth: 2,
    barGap: 1,
    barRadius: 2,
    cursorWidth: 1,
    waveColor: themeColour('gold', 0.32),
    progressColor: themeColour('gold-light', 0.95),
    cursorColor: themeColour('gold-pale', 0.9),
    interact: true,
    hideScrollbar: true,
    plugins: [regions],
  })
  // The waveform only draws the player: playing is the site player's job (it keeps going across pages)
  ws.on('interaction', (seconds) => emit('seek', seconds))
  ws.on('ready', (duration) => {
    ready.value = true
    ws!.setTime(props.time)
    paintStretches()
    paintSelection()
    emit('ready', duration)
  })

  if (props.selectable) {
    regions.enableDragSelection({ color: themeColour('gold', 0.28), id: SELECTION })
    regions.on('region-created', (region) => {
      if (region.id.startsWith('c-')) return
      // one selection at a time: the newest one replaces the old
      for (const other of regions!.getRegions()) if (other !== region && !other.id.startsWith('c-')) other.remove()
      region.setOptions({ id: SELECTION })
      emit('select', { start: region.start, end: region.end })
    })
    regions.on('region-updated', (region) => {
      if (!region.id.startsWith('c-')) emit('select', { start: region.start, end: region.end })
    })
  }
  regions.on('region-clicked', (region, e) => {
    if (!region.id.startsWith('c-')) return
    e.stopPropagation()
    const found = props.stretches.find((s) => `c-${s.id}` === region.id)
    if (found) emit('stretch', found)
  })
}

/** The comments' stretches: lit, not movable */
function paintStretches() {
  if (!regions || !ready.value) return
  for (const r of regions.getRegions()) if (r.id.startsWith('c-')) r.remove()
  for (const s of props.stretches) {
    regions.addRegion({ id: `c-${s.id}`, start: s.start, end: s.end, color: themeColour('gold', 0.13), drag: false, resize: false })
  }
}

/** A selection set from outside (cleared after a comment is sent, or by ✕) */
function paintSelection() {
  if (!regions || !ready.value) return
  const current = regions.getRegions().find((r) => r.id === SELECTION)
  if (!props.selection) return current?.remove()
  if (current && Math.abs(current.start - props.selection.start) < 0.05 && Math.abs(current.end - props.selection.end) < 0.05) return
  current?.remove()
  regions.addRegion({ id: SELECTION, ...props.selection, color: themeColour('gold', 0.28) })
}

watch(() => props.time, (t) => {
  if (ws && ready.value) ws.setTime(t)
})
watch(() => props.stretches, paintStretches, { deep: true })
watch(() => props.selection, paintSelection, { deep: true })

onMounted(build)
onBeforeUnmount(() => {
  ws?.destroy()
  ws = null
  regions = null
})
</script>

<style scoped>
/* a horizontal drag along the waveform selects; the page still scrolls up and down */
.audio-wave.selectable { touch-action: pan-y; }
.audio-wave :deep([part~='region-handle-left']),
.audio-wave :deep([part~='region-handle-right']) { border-color: rgb(var(--c-gold-light)) !important; width: 8px !important; }
</style>
