<template>
  <!-- MusicXML / MXL rendered by OpenSheetMusicDisplay; a golden runner moves along the notes with the recording.
       «Страницами»: exactly one page on screen, as in the printed edition (page breaks written into the file by
       MuseScore, Sibelius, Dorico…; otherwise screen-sized pages) — the leaf turns when the music reaches its end.
       «Лентой»: the whole score as one scrolling strip. -->
  <div>
    <div class="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2">
      <span class="font-caps text-base font-semibold tracking-[0.15em] text-parchment-muted">
        <template v-if="layout === 'pages'">
          Стр. <span class="font-display text-lg text-gold-light">{{ page }}</span> из {{ pages.length }} ·
        </template>
        Такт <span class="font-display text-lg text-gold-light">{{ measure }}</span><span v-if="measureCount"> из {{ measureCount }}</span>
      </span>
      <div class="ml-auto flex flex-wrap items-center gap-2">
        <template v-if="layout === 'pages'">
          <button type="button" class="chip px-2" :disabled="page <= 1" aria-label="Предыдущая страница" @click="browse(page - 1)">‹</button>
          <button type="button" class="chip px-2" :disabled="page >= pages.length" aria-label="Следующая страница" @click="browse(page + 1)">›</button>
        </template>
        <button type="button" class="chip" :class="{ active: layout === 'pages' }" @click="setLayout('pages')">Страницами</button>
        <button type="button" class="chip" :class="{ active: layout === 'scroll' }" @click="setLayout('scroll')">Лентой</button>
        <button type="button" class="chip px-2" aria-label="Мельче" :disabled="zoom <= 0.4" @click="setZoom(zoom - 0.1)">−</button>
        <button type="button" class="chip px-2" aria-label="Крупнее" :disabled="zoom >= 1.6" @click="setZoom(zoom + 0.1)">+</button>
        <button
          v-if="opus.audio_type !== 'none'"
          type="button"
          class="chip"
          :class="{ active: follow }"
          :title="follow ? 'Бегунок и страницы идут за записью' : 'Вернуться к месту, которое сейчас звучит'"
          @click="enableFollow"
        >
          {{ follow ? '⟳ За записью' : '⟳ Следовать' }}
        </button>
      </div>
    </div>

    <div class="frame frame-thin">
      <div class="frame-inner bg-[#f5efe0]" style="perspective: 2400px">
        <div
          ref="scroller"
          class="max-h-[78vh] min-h-[24rem] overflow-y-auto overscroll-contain lg:max-h-[calc(100vh-17rem)]"
          tabindex="0"
          @scroll.passive="onScroll"
          @scrollend="autoScrolling = false"
          @wheel.passive="pauseFollow"
          @touchmove.passive="pauseFollow"
          @keydown="onKey"
          @pointerdown="onPointerDown"
        >
          <!-- One page = a window onto the full rendering (OSMD's cursor is only reliable on a complete layout) -->
          <div ref="clip" class="relative overflow-hidden" :style="clipStyle">
            <!-- isolate: OSMD puts the cursor at z-index -1; keep it above the paper, below the notes -->
            <div ref="host" class="relative isolate cursor-pointer px-2 py-4" :style="hostStyle" @click="onClick" />
          </div>
          <p v-if="!ready" class="py-24 text-center font-elegant text-xl italic text-ink-600">{{ error || 'Партитура загружается…' }}</p>
        </div>
        <!-- The turning leaf: a snapshot of the page being left -->
        <div ref="leafHost" class="pointer-events-none absolute inset-0 z-20" />
      </div>
    </div>
    <p class="mt-2 text-sm italic text-parchment-faint">Клик по ноте — перемотка записи к этому месту.</p>
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { Opus } from '~/utils/types'

const props = defineProps<{ opus: Opus }>()
const emit = defineEmits<{ seek: [seconds: number] }>()
defineExpose({ enableFollow: () => enableFollow() })

const LAYOUT_KEY = 'allegro-score-layout'
const player = usePlayer()
const host = ref<HTMLElement>()
const scroller = ref<HTMLElement>()
const leafHost = ref<HTMLElement>()
const clip = ref<HTMLElement>()
/** Pixel window of each page inside the full rendering */
const pageBoxes = ref<{ top: number; height: number }[]>([])
const clipStyle = computed(() => {
  const box = layout.value === 'pages' ? pageBoxes.value[page.value - 1] : null
  return box ? { height: `${box.height}px` } : {}
})
const hostStyle = computed(() => {
  const box = layout.value === 'pages' ? pageBoxes.value[page.value - 1] : null
  return box ? { transform: `translateY(${-box.top}px)` } : {}
})
const ready = ref(false)
const error = ref('')
const follow = ref(true)
const zoom = ref(0.85)
/** true until the reader presses −/+: pages are scaled to fit the screen */
const autoFit = ref(true)
const layout = ref<'pages' | 'scroll'>('pages')
const measure = ref(1)
const measureCount = ref(0)
const page = ref(1)
/** Page = a range of ordinal measures */
const pages = ref<{ start: number; end: number }[]>([{ start: 1, end: 1 }])

interface Step {
  iterator: any // cloned MusicPartManagerIterator: restores the cursor position, repeats included
  sourceTs: number // position in the score (whole notes)
  scoreSec: number // seconds from the first beat at the written tempo
  audioSec: number // second of the recording
  measure: number // ordinal, 1-based
}

let osmd: any = null
let PointF2D: any = null
let steps: Step[] = []
let current = 0

// ---------------------------------------------------------------- timeline

/** Walk the score once, integrating the written tempo into seconds */
function buildTimeline() {
  const it = osmd.Sheet.MusicPartManager.getIterator()
  let bpm = it.CurrentBpm || osmd.Sheet.DefaultStartTempoInBpm || 100
  let prevTs = 0
  let sec = 0
  const result: Step[] = []
  let guard = 0
  while (!it.EndReached && guard++ < 50000) {
    const ts = it.CurrentEnrolledTimestamp.RealValue
    sec += ((ts - prevTs) * 240) / bpm // a whole note is four quarter beats
    prevTs = ts
    if (it.CurrentBpm) bpm = it.CurrentBpm
    result.push({
      iterator: it.clone(),
      sourceTs: it.CurrentSourceTimestamp.RealValue,
      scoreSec: sec,
      audioSec: 0,
      measure: it.CurrentMeasureIndex + 1,
    })
    it.moveToNext()
  }
  steps = result
  measureCount.value = osmd.Sheet.SourceMeasures?.length || (result.length ? Math.max(...result.map((s) => s.measure)) : 0)
  applySync()
}

/**
 * Score time → recording time. Without measure markers: offset + written tempo.
 * With markers (live performance with rubato): piecewise-linear between the pinned measures.
 * The server applies the same rule to turn PDF pages (allegro_common/musicxml.py).
 */
function applySync() {
  const anchors = props.opus.measure_markers
    .map((m) => {
      const first = steps.find((s) => s.measure === m.measure_number)
      return first ? { score: first.scoreSec, audio: m.timestamp_seconds } : null
    })
    .filter((a): a is { score: number; audio: number } => !!a)
    .sort((a, b) => a.score - b.score)

  const map = (s: number) => {
    if (!anchors.length) return (props.opus.audio_offset_seconds || 0) + s
    if (s <= anchors[0].score) return anchors[0].audio + (s - anchors[0].score)
    const last = anchors[anchors.length - 1]
    if (s >= last.score) return last.audio + (s - last.score)
    const i = anchors.findIndex((a) => a.score > s)
    const a = anchors[i - 1]
    const b = anchors[i]
    return a.audio + ((s - a.score) / (b.score - a.score)) * (b.audio - a.audio)
  }
  steps.forEach((s) => (s.audioSec = map(s.scoreSec)))
}

/** Last step that has started by `time` (binary search) */
function stepAt(time: number) {
  let lo = 0
  let hi = steps.length - 1
  let found = 0
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (steps[mid].audioSec <= time + 0.03) {
      found = mid
      lo = mid + 1
    } else hi = mid - 1
  }
  return found
}

// ---------------------------------------------------------------- rendering

const availableHeight = () => {
  const box = scroller.value
  if (!box) return 700
  const max = parseFloat(getComputedStyle(box).maxHeight)
  return (Number.isFinite(max) ? max : box.clientHeight) - 8
}

// setOptions() resets cursor options to OSMD defaults (green), so pass ours every time
const CURSOR = [{ type: 0, color: '#c98a1e', alpha: 0.55, follow: false }]

/** Render the whole score (OSMD's cursor needs the complete layout) */
function draw() {
  osmd.setOptions({ cursorsOptions: CURSOR })
  osmd.zoom = zoom.value
  osmd.render()
  osmd.cursor.show()
}

/** Systems of the rendering in pixels, with the ordinal of their first measure */
function systemsPx() {
  const unit = 10 * zoom.value
  const pad = 16 // host padding-top (py-4)
  const systems: any[] = osmd.GraphicSheet.MusicPages.flatMap((p: any) => p.MusicSystems)
  return systems.map((sys: any) => {
    const top = sys.PositionAndShape.AbsolutePosition.y * unit + pad
    return {
      first: (sys.GraphicalMeasures?.[0]?.[0]?.parentSourceMeasure?.measureListIndex ?? 0) + 1,
      top: top + sys.PositionAndShape.BorderTop * unit,
      bottom: top + sys.PositionAndShape.BorderBottom * unit,
    }
  })
}

/**
 * Pages: printed page breaks from the file (MuseScore, Sibelius, Dorico… write them), or systems grouped
 * so that each page fits the screen. A page is a pixel window [top, top + height) of the full rendering.
 */
function computePages() {
  const total = osmd.Sheet.SourceMeasures.length
  const systems = systemsPx()
  if (!systems.length) return
  const starts = [1]
  osmd.Sheet.SourceMeasures.forEach((m: any, i: number) => {
    if (i > 0 && m.printNewPageXml) starts.push(i + 1)
  })
  if (starts.length === 1) {
    const limit = availableHeight() - 24
    let pageTop = 0
    systems.forEach((sys, i) => {
      if (i > 0 && sys.bottom - pageTop > limit && sys.first > starts[starts.length - 1]) {
        starts.push(sys.first)
        pageTop = (systems[i - 1].bottom + sys.top) / 2
      }
    })
  }
  pages.value = starts.map((start, i) => ({ start, end: (starts[i + 1] ?? total + 1) - 1 }))

  // Page windows: cut between the last system of a page and the first system of the next one
  const contentBottom = (host.value?.scrollHeight ?? systems[systems.length - 1].bottom + 16)
  const cuts = starts.map((start, i) => {
    if (i === 0) return 0
    const idx = systems.findIndex((sys) => sys.first >= start)
    if (idx <= 0) return systems[Math.max(idx, 0)]?.top ?? 0
    return Math.round((systems[idx - 1].bottom + systems[idx].top) / 2)
  })
  pageBoxes.value = cuts.map((top, i) => ({ top, height: (cuts[i + 1] ?? contentBottom) - top }))
}

const pageOfMeasure = (m: number) => Math.max(1, pages.value.filter((p) => p.start <= m).length)

/** Show one page; unless the reader chose a zoom, scale so a whole page fits (down to a readable size) */
function drawPage(p: number) {
  if (!pages.value[p - 1]) return
  page.value = p
  scrollBox(0, 'auto')
}

function layoutPages() {
  const MIN_FIT = 0.55
  if (autoFit.value) zoom.value = 0.85
  draw()
  computePages()
  for (let i = 0; autoFit.value && i < 3; i++) {
    const tallest = Math.max(...pageBoxes.value.map((b) => b.height))
    const limit = availableHeight()
    if (tallest <= limit || zoom.value <= MIN_FIT) break
    zoom.value = Math.max(MIN_FIT, Math.floor(zoom.value * (limit / tallest) * 0.97 * 100) / 100)
    draw()
    computePages()
  }
}

function render() {
  if (layout.value === 'pages') {
    layoutPages()
    drawPage(pageOfMeasure(steps[current]?.measure ?? 1))
  } else {
    pageBoxes.value = []
    draw()
  }
  nextTick(() => {
    placeCursor(current)
    if (layout.value === 'scroll') scrollBox(current <= 0 ? 0 : cursorTop(), 'auto')
    else keepInView()
  })
}

/** A page turns like a leaf of a book: snapshot the visible page, draw the next one, fold the snapshot away */
function turnTo(p: number) {
  if (!host.value || !leafHost.value || !scroller.value) return
  const forward = p > page.value
  const leaf = document.createElement('div')
  leaf.style.cssText = `position:absolute;inset:0;overflow:hidden;background:#f5efe0;transform-origin:${forward ? 'left' : 'right'} center;box-shadow:${forward ? '' : '-'}18px 0 40px -10px rgba(0,0,0,.6);`
  const snapshot = (clip.value ?? host.value).cloneNode(true) as HTMLElement
  snapshot.style.transform = `translateY(${-scroller.value.scrollTop}px)`
  leaf.appendChild(snapshot)
  leafHost.value.replaceChildren(leaf)

  drawPage(p)
  nextTick(() => placeCursor(current))

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
  const animation = leaf.animate(
    [
      { transform: 'rotateY(0deg)', filter: 'brightness(1)', opacity: 1 },
      { transform: `rotateY(${forward ? -105 : 105}deg)`, filter: 'brightness(.45) sepia(.4)', opacity: 0.35 },
    ],
    { duration: reduced ? 1 : 850, easing: 'cubic-bezier(.6,.05,.3,1)' },
  )
  animation.onfinish = () => leaf.remove()
}

/** Reader flips pages by hand: stop following until «Следовать» */
function browse(p: number) {
  if (p < 1 || p > pages.value.length) return
  follow.value = false
  turnTo(p)
  placeCursor(current)
}

// ---------------------------------------------------------------- cursor

/** OSMD stretches a 1px-high cursor image via the height attribute; Tailwind's `img { height: auto }` would undo it */
function fixCursorSize() {
  const el: HTMLImageElement | undefined = osmd?.cursor?.cursorElement
  if (el) {
    // Read the attribute: the `height` property reports the rendered (CSS-squashed) height
    const height = Number(el.getAttribute('height'))
    if (height > 1) el.style.height = `${height}px`
    el.style.maxWidth = 'none'
  }
}

/** Put the golden runner on a step (hidden if that measure is on another page) */
function placeCursor(index: number) {
  const step = steps[index]
  if (!osmd || !step) return
  const range = pages.value[page.value - 1]
  const visible = layout.value === 'scroll' || (range && step.measure >= range.start && step.measure <= range.end)
  if (!visible) return osmd.cursor.hide()
  try {
    osmd.cursor.show()
    osmd.cursor.iterator = step.iterator.clone()
    osmd.cursor.update()
    fixCursorSize()
  } catch {
    osmd.cursor.hide()
  }
}

function moveTo(index: number, followView = true) {
  if (!osmd || !steps[index]) return
  current = index
  measure.value = steps[index].measure
  if (layout.value === 'pages' && followView) {
    const p = pageOfMeasure(measure.value)
    if (p !== page.value) turnTo(p) // the music reached the next page: turn the leaf
  }
  placeCursor(index)
  if (followView) keepInView()
}

/** Cursor position inside the scroll box (measured, since OSMD may nest containers) */
function cursorBox(): { top: number; bottom: number } | null {
  const el: HTMLElement | undefined = osmd?.cursor?.cursorElement
  const box = scroller.value
  if (!el || !box || el.style.display === 'none') return null
  const r = el.getBoundingClientRect()
  const b = box.getBoundingClientRect()
  return { top: r.top - b.top + box.scrollTop, bottom: r.bottom - b.top + box.scrollTop }
}

const cursorTop = () => (cursorBox()?.top ?? 16) - 16

/** Our own scrolling: until it ends (scrollend, or a timeout) scroll events are not the reader's */
const autoScrolling = ref(false)
let autoTimer: ReturnType<typeof setTimeout> | undefined
function scrollBox(top: number, behavior: ScrollBehavior) {
  const box = scroller.value
  if (!box) return
  autoScrolling.value = true
  clearTimeout(autoTimer)
  autoTimer = setTimeout(() => (autoScrolling.value = false), behavior === 'smooth' ? 2500 : 300)
  box.scrollTo({ top: Math.max(0, top), behavior })
}

/** Keep the runner in the upper part of the box (only needed when a page is taller than the screen, or in «Лентой») */
function keepInView() {
  const c = cursorBox()
  const box = scroller.value
  if (!c || !box) return
  if (c.top < box.scrollTop + 40 || c.bottom > box.scrollTop + box.clientHeight - 40) {
    scrollBox(c.top - box.clientHeight * 0.25, 'smooth')
  }
}

/** The reader takes over (wheel, touch, keys, scrollbar drag): stop following until «Следовать» */
function pauseFollow() {
  autoScrolling.value = false
  follow.value = false
}
let dragging = false
function onScroll() {
  if (!autoScrolling.value && dragging) follow.value = false
}
function onPointerDown(e: PointerEvent) {
  const box = scroller.value
  if (box && e.offsetX > box.clientWidth) {
    dragging = true
    pauseFollow()
    window.addEventListener('pointerup', () => (dragging = false), { once: true })
  }
}
function onKey(e: KeyboardEvent) {
  if (['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '].includes(e.key)) pauseFollow()
}

function enableFollow() {
  follow.value = true
  const index = player.isCurrent(props.opus.slug) ? stepAt(player.time) : current
  if (layout.value === 'pages') {
    const p = pageOfMeasure(steps[index]?.measure ?? 1)
    if (p !== page.value) turnTo(p)
  }
  moveTo(index)
}

watch(() => (player.isCurrent(props.opus.slug) ? player.time : null), (time) => {
  if (time == null || !steps.length) return
  const index = stepAt(time)
  if (index !== current) moveTo(index, follow.value)
})

// Click on a note → seek the recording to it
function onClick(e: MouseEvent) {
  if (!osmd || !steps.length || props.opus.audio_type === 'none') return
  try {
    const sheet = osmd.GraphicSheet
    const point = sheet.svgToOsmd(sheet.domToSvg(new PointF2D(e.clientX, e.clientY)))
    const entry = sheet.GetNearestStaffEntry(point)
    if (!entry) return
    const ts = entry.getAbsoluteTimestamp().RealValue
    const index = steps.findIndex((s) => s.sourceTs >= ts - 1e-6)
    if (index < 0) return
    follow.value = true
    moveTo(index, false)
    emit('seek', Math.max(0, steps[index].audioSec))
  } catch (err) {
    console.warn('Score click not resolved', err)
  }
}

// ---------------------------------------------------------------- controls

function setZoom(value: number) {
  autoFit.value = false
  zoom.value = Math.round(Math.min(1.6, Math.max(0.4, value)) * 10) / 10
  if (ready.value) render()
}

function setLayout(value: 'pages' | 'scroll') {
  if (layout.value === value) return
  layout.value = value
  autoFit.value = value === 'pages'
  if (value === 'scroll') zoom.value = 0.85
  try {
    localStorage.setItem(LAYOUT_KEY, value)
  } catch {}
  if (ready.value) render()
}

let resizeTimer: ReturnType<typeof setTimeout> | undefined
let lastSize = ''
const onResize = () => {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    const size = `${Math.round((host.value?.clientWidth || 0) / 40)}x${Math.round(window.innerHeight / 40)}`
    if (ready.value && size !== lastSize) {
      lastSize = size
      render()
    }
  }, 300)
}

onMounted(async () => {
  try {
    const saved = localStorage.getItem(LAYOUT_KEY)
    if (saved === 'pages' || saved === 'scroll') layout.value = saved
  } catch {}
  autoFit.value = layout.value === 'pages'
  try {
    const lib = await import('opensheetmusicdisplay')
    PointF2D = lib.PointF2D
    osmd = new lib.OpenSheetMusicDisplay(host.value!, {
      backend: 'svg',
      autoResize: false, // re-rendered by onResize, keeping the runner position
      autoBeam: true,
      drawTitle: true,
      drawComposer: true,
      drawPartNames: true,
      pageFormat: 'Endless',
      newSystemFromXML: true, // keep the line breaks of the export, like its PDF
      newSystemFromNewPageInXML: true, // a printed page always starts on a new line
      followCursor: false, // we scroll the score box ourselves, not the page
      defaultColorMusic: '#1c140e',
      cursorsOptions: CURSOR,
    })
    // Compressed .mxl is a ZIP: hand OSMD a Blob; plain MusicXML as text
    const buffer = await (await fetch(props.opus.musicxml_url!)).arrayBuffer()
    const bytes = new Uint8Array(buffer)
    const isZip = bytes[0] === 0x50 && bytes[1] === 0x4b
    await osmd.load(isZip ? new Blob([buffer]) : new TextDecoder().decode(bytes), props.opus.title)
    ready.value = true
    await nextTick()
    lastSize = `${Math.round((host.value?.clientWidth || 0) / 40)}x${Math.round(window.innerHeight / 40)}`
    buildTimeline()
    current = player.isCurrent(props.opus.slug) ? stepAt(player.time) : 0
    measure.value = steps[current]?.measure ?? 1
    render()
    window.addEventListener('resize', onResize)
  } catch (e) {
    console.error(e)
    error.value = 'Не удалось открыть MusicXML'
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  clearTimeout(resizeTimer)
  clearTimeout(autoTimer)
  osmd?.clear?.()
})
</script>
