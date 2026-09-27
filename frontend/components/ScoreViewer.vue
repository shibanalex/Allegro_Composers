<template>
  <!-- PDF.js score viewer: pages turn by themselves as the recording crosses the sync markers -->
  <div ref="root">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <button class="btn-ghost px-2 text-xl" :disabled="page <= 1" aria-label="Предыдущая страница" @click="manual(page - 1)">‹</button>
      <span class="font-caps text-base font-semibold tracking-[0.15em] text-parchment-muted">
        Стр. <span class="font-display text-lg text-gold-light">{{ page }}</span> из {{ pageCount }}
      </span>
      <button class="btn-ghost px-2 text-xl" :disabled="page >= pageCount" aria-label="Следующая страница" @click="manual(page + 1)">›</button>

      <button
        v-if="opus.markers.length && opus.audio_type !== 'none'"
        type="button"
        class="chip ml-auto"
        :class="{ active: follow }"
        :title="follow ? 'Страницы листаются вслед за записью' : 'Включить автоперелистывание'"
        @click="enableFollow"
      >
        {{ follow ? '⟳ Листать за записью' : '⟳ Следовать за записью' }}
      </button>
    </div>

    <div class="book">
      <Transition :name="direction > 0 ? 'turn-next' : 'turn-prev'">
        <div :key="page" class="frame frame-thin">
          <div class="frame-inner bg-[#f5efe0]" :style="{ aspectRatio: aspect }">
            <img v-if="images[page]" :src="images[page]" :alt="`Страница ${page}`" class="h-full w-full select-none" draggable="false">
            <div v-else class="flex h-full items-center justify-center font-elegant text-xl italic text-ink-600">
              {{ error || 'Партитура загружается…' }}
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Runner: where the recording is within the visible page -->
    <div v-if="pageProgress != null" class="mt-3 h-[3px] w-full bg-gold/15" aria-hidden="true">
      <div class="h-full bg-gradient-to-r from-gold-dark via-gold to-gold-light shadow-[0_0_8px_rgba(201,163,106,.7)] transition-[width] duration-300 ease-linear" :style="{ width: `${pageProgress * 100}%` }" />
    </div>

    <!-- Page ↔ time map: jump to the moment a page starts -->
    <div v-if="opus.markers.length && opus.audio_type !== 'none'" class="mt-5 flex flex-wrap gap-2">
      <button
        v-for="m in opus.markers"
        :key="m.page_number"
        type="button"
        class="chip"
        :class="{ active: m.page_number === page }"
        @click="$emit('seek', m.timestamp_seconds)"
      >
        стр. {{ m.page_number }} · <span class="ml-1 font-mono text-xs">{{ formatTime(m.timestamp_seconds) }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { pageAt, usePlayer } from '~/stores/player'
import type { Opus } from '~/utils/types'

const props = defineProps<{ opus: Opus }>()
defineEmits<{ seek: [seconds: number] }>()
defineExpose({ enableFollow: () => enableFollow() })

const player = usePlayer()
const root = ref<HTMLElement>()
const page = ref(1)
const direction = ref(1)
const follow = ref(true)
const images = reactive<Record<number, string>>({})
const aspect = ref('1 / 1.414')
const error = ref('')
const pageCount = computed(() => props.opus.score_page_count || 1)

/** 0..1 through the visible page, from its marker to the next page's marker (or the end of the recording) */
const pageProgress = computed(() => {
  if (!player.isCurrent(props.opus.slug) || !props.opus.markers.length) return null
  const markers = props.opus.markers
  const start = markers.find((m) => m.page_number === page.value)?.timestamp_seconds
  if (start == null) return null
  const next = markers.find((m) => m.page_number > page.value)?.timestamp_seconds ?? player.duration
  if (!next || next <= start) return null
  return Math.min(1, Math.max(0, (player.time - start) / (next - start)))
})

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

async function goTo(n: number) {
  n = Math.min(Math.max(1, n), pageCount.value)
  if (n === page.value) return
  await render(n)
  direction.value = n > page.value ? 1 : -1
  page.value = n
  render(n + 1) // pre-render the next leaf so the turn is instant
}

function manual(n: number) {
  follow.value = false
  goTo(n)
}

function enableFollow() {
  follow.value = true
  if (player.isCurrent(props.opus.slug)) {
    const target = pageAt(props.opus.markers, player.time)
    if (target) goTo(target)
  }
}

// Follow the recording
watch(() => player.isCurrent(props.opus.slug) ? player.time : null, (time) => {
  if (time == null || !follow.value) return
  const target = pageAt(props.opus.markers, time)
  if (target && target !== page.value) goTo(target)
})

let resizeTimer: ReturnType<typeof setTimeout> | undefined
const onResize = () => {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    const width = root.value?.clientWidth || 0
    if (Math.abs(width - renderWidth) < 40) return
    renderWidth = width
    Object.keys(images).forEach((k) => delete images[Number(k)])
    render(page.value)
  }, 250)
}

onMounted(async () => {
  try {
    const pdfjs = await import('pdfjs-dist')
    const worker = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
    pdfjs.GlobalWorkerOptions.workerSrc = worker.default
    pdf = await pdfjs.getDocument(props.opus.score_url!).promise
    renderWidth = root.value?.clientWidth || 800
    if (player.isCurrent(props.opus.slug)) page.value = pageAt(props.opus.markers, player.time) || 1
    await render(page.value)
    render(page.value + 1)
    window.addEventListener('resize', onResize)
  } catch (e) {
    console.error(e)
    error.value = 'Не удалось открыть партитуру'
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  pdf?.destroy?.()
})
</script>
