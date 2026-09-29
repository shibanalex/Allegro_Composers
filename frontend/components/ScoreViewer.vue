<template>
  <!-- PDF.js score viewer: the reader turns the pages like a book (click, arrows, swipe); the recording doesn't turn them -->
  <div ref="root" class="score-viewer" :class="{ 'is-fullscreen': fullscreen }">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <span class="font-caps text-base font-semibold tracking-[0.15em] text-parchment-muted">
        Стр. <span class="font-display text-lg text-gold-light">{{ page }}</span> из {{ pageCount }}
      </span>

      <div class="ml-auto flex flex-wrap items-center gap-2">
        <button v-if="canFullscreen" type="button" class="chip" :title="fullscreen ? 'Выйти (Esc)' : 'Страница целиком на весь экран'" @click="toggleFullscreen">
          {{ fullscreen ? '✕ Свернуть' : '⛶ Во весь экран' }}
        </button>
      </div>
    </div>

    <!-- The page: click the right half to turn forward, the left half to turn back; swipe on touch screens -->
    <div class="book group touch-pan-y" @pointerdown="onPointerDown" @pointerup="onPointerUp">
      <Transition :name="direction > 0 ? 'turn-next' : 'turn-prev'">
        <div :key="page" class="frame frame-thin mx-auto" :style="frameStyle">
          <div class="frame-inner bg-[#f5efe0]" :style="{ aspectRatio: aspect }">
            <img v-if="images[page]" :src="images[page]" :alt="`Страница ${page}`" class="h-full w-full select-none" draggable="false">
            <div v-else class="flex h-full items-center justify-center font-elegant text-xl italic text-ink-600">
              {{ error || 'Партитура загружается…' }}
            </div>
          </div>
        </div>
      </Transition>

      <button
        type="button"
        class="page-zone left-0 cursor-w-resize justify-start"
        :disabled="page <= 1"
        aria-label="Предыдущая страница"
        @click="zoneClick(-1)"
      >
        <span class="page-zone-arrow">‹</span>
      </button>
      <button
        type="button"
        class="page-zone right-0 cursor-e-resize justify-end"
        :disabled="page >= pageCount"
        aria-label="Следующая страница"
        @click="zoneClick(1)"
      >
        <span class="page-zone-arrow">›</span>
      </button>
    </div>

    <!-- Always at hand while reading a tall page -->
    <div class="pager" :style="{ bottom: otherTrackPlaying && !fullscreen ? '6.5rem' : '1.5rem' }">
      <button type="button" class="pager-btn" :disabled="page <= 1" aria-label="Предыдущая страница" @click="manual(page - 1)">‹</button>
      <span class="min-w-[4.5rem] text-center font-caps text-sm font-semibold tracking-[0.15em] text-parchment-muted">
        <span class="font-display text-base text-gold-light">{{ page }}</span> / {{ pageCount }}
      </span>
      <button type="button" class="pager-btn" :disabled="page >= pageCount" aria-label="Следующая страница" @click="manual(page + 1)">›</button>
    </div>

    <!-- All pages: open any of them -->
    <div v-if="pageCount > 1 && !fullscreen" class="mt-5 flex flex-wrap gap-2">
      <button
        v-for="n in pageCount"
        :key="n"
        type="button"
        class="chip"
        :class="{ active: n === page }"
        @click="manual(n)"
      >
        стр. {{ n }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { Opus } from '~/utils/types'

const props = defineProps<{ opus: Opus }>()

const player = usePlayer()
const root = ref<HTMLElement>()
const page = ref(1)
const direction = ref(1)
const images = reactive<Record<number, string>>({})
const aspect = ref('1 / 1.414')
const error = ref('')
const numPages = ref(0)
// The PDF itself knows best; the stored count is only a first guess before it loads
const pageCount = computed(() => numPages.value || props.opus.score_page_count || 1)
// The site's bottom player bar shows only for another work (this page has its own player on top)
const otherTrackPlaying = computed(() => !!player.track && player.track.slug !== props.opus.slug)


// ---------------------------------------------------------------- rendering

let pdf: any = null
let renderWidth = 0
const rendering = new Map<number, Promise<void>>()

async function render(n: number) {
  if (!pdf || n < 1 || n > pdf.numPages || images[n]) return
  if (rendering.has(n)) return rendering.get(n)
  const task = (async () => {
    const pdfPage = await pdf.getPage(n)
    const base = pdfPage.getViewport({ scale: 1 })
    const scale = (renderWidth * Math.min(window.devicePixelRatio || 1, 2)) / base.width
    const viewport = pdfPage.getViewport({ scale })
    const canvas = document.createElement('canvas')
    canvas.width = viewport.width
    canvas.height = viewport.height
    await pdfPage.render({ canvasContext: canvas.getContext('2d')!, viewport }).promise
    images[n] = canvas.toDataURL('image/jpeg', 0.92)
    if (n === 1) aspect.value = `${base.width} / ${base.height}`
  })().finally(() => rendering.delete(n))
  rendering.set(n, task)
  return task
}

// ---------------------------------------------------------------- turning

async function goTo(n: number) {
  n = Math.min(Math.max(1, n), pageCount.value)
  if (n === page.value) return
  await render(n)
  direction.value = n > page.value ? 1 : -1
  page.value = n
  showPageTop()
  render(n + 1) // pre-render the neighbours so the next turn is instant
  render(n - 1)
}

/** Turned by the reader */
function manual(n: number) {
  goTo(n)
}


/** A tall page is read top to bottom: after a turn, bring the new page's top into view (under the sticky bars) */
function showPageTop() {
  if (fullscreen.value || !root.value) return
  const rect = root.value.getBoundingClientRect()
  const covered = 190 // site header + the opus's sticky player
  const visible = rect.bottom > covered && rect.top < window.innerHeight
  if (visible && rect.top < covered) window.scrollBy({ top: rect.top - covered, behavior: 'smooth' })
}

// Click zones and swipes
let downX = 0
let downY = 0
let swiped = false
const onPointerDown = (e: PointerEvent) => {
  downX = e.clientX
  downY = e.clientY
  swiped = false
}
const onPointerUp = (e: PointerEvent) => {
  const dx = e.clientX - downX
  const dy = e.clientY - downY
  if (e.pointerType !== 'mouse' && Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
    swiped = true
    manual(page.value + (dx < 0 ? 1 : -1))
  }
}
const zoneClick = (step: number) => {
  if (swiped) return // the swipe already turned the page
  manual(page.value + step)
}

// Arrow keys, unless the reader is typing somewhere
function onKey(e: KeyboardEvent) {
  if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return
  const target = e.target as HTMLElement | null
  if (target?.closest('input, textarea, select, [contenteditable="true"]')) return
  if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
  const rect = root.value?.getBoundingClientRect()
  if (!rect || rect.bottom < 0 || rect.top > window.innerHeight) return // the score isn't on screen
  e.preventDefault()
  manual(page.value + (e.key === 'ArrowRight' ? 1 : -1))
}


// ---------------------------------------------------------------- full screen: the whole page fits the screen

const fullscreen = ref(false)
const canFullscreen = ref(false)
const aspectNumber = computed(() => {
  const [w, h] = aspect.value.split('/').map(Number)
  return w && h ? w / h : 1 / 1.414
})
const frameStyle = computed(() =>
  fullscreen.value ? { width: `min(100%, calc((100vh - 9rem) * ${aspectNumber.value}))` } : undefined,
)
function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen()
  else root.value?.requestFullscreen?.()
}
const onFullscreenChange = () => {
  fullscreen.value = document.fullscreenElement === root.value
}

// ---------------------------------------------------------------- lifecycle

let resizeTimer: ReturnType<typeof setTimeout> | undefined
const onResize = () => {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    const width = root.value?.clientWidth || 0
    if (Math.abs(width - renderWidth) < 40) return
    renderWidth = width
    Object.keys(images).forEach((k) => delete images[Number(k)])
    render(page.value)
    render(page.value + 1)
  }, 250)
}

onMounted(async () => {
  canFullscreen.value = !!document.fullscreenEnabled
  window.addEventListener('keydown', onKey)
  document.addEventListener('fullscreenchange', onFullscreenChange)
  try {
    const pdfjs = await import('pdfjs-dist')
    const worker = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
    pdfjs.GlobalWorkerOptions.workerSrc = worker.default
    pdf = await pdfjs.getDocument(props.opus.score_url!).promise
    numPages.value = pdf.numPages
    renderWidth = root.value?.clientWidth || 800
    await render(page.value)
    render(page.value + 1)
    window.addEventListener('resize', onResize)
  } catch (e) {
    console.error(e)
    error.value = 'Не удалось открыть партитуру'
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onResize)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  if (document.fullscreenElement === root.value) document.exitFullscreen()
  pdf?.destroy?.()
})
</script>

<style scoped>
/* Invisible halves of the page that turn it; an arrow appears at the edge on hover */
.page-zone {
  @apply absolute inset-y-0 z-30 flex w-1/2 items-center px-3 disabled:cursor-default;
  -webkit-tap-highlight-color: transparent;
}
.page-zone-arrow {
  @apply flex h-14 w-14 items-center justify-center rounded-full border border-gold/40 bg-ink-950/75 font-display text-4xl leading-none text-gold-light opacity-0 shadow-lg transition-opacity duration-200;
}
.group:hover .page-zone:not(:disabled) .page-zone-arrow,
.page-zone:focus-visible .page-zone-arrow {
  @apply opacity-100;
}

/* Pinned to the bottom of the screen while the score is in view */
.pager {
  @apply sticky z-40 mx-auto mt-4 flex w-fit items-center gap-1 rounded-full border border-gold/30 bg-ink-950/90 px-2 py-1 shadow-[0_10px_30px_-10px_rgba(0,0,0,.9)] backdrop-blur;
}
.pager-btn {
  @apply flex h-10 w-10 items-center justify-center rounded-full font-display text-2xl text-gold-light transition hover:bg-gold/15 disabled:opacity-30 disabled:hover:bg-transparent;
}

/* Full screen: dark stage, the page fitted to the screen height */
.score-viewer.is-fullscreen {
  @apply overflow-auto bg-ink-950 px-4 py-4 sm:px-10;
}
</style>
