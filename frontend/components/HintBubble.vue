<template>
  <!-- The element the hint is about; the bubble itself is drawn over the whole page, so no section can cover it -->
  <div ref="root">
    <slot />
    <Teleport to="body">
      <Transition name="hint">
        <div
          v-if="open && place"
          ref="bubble"
          role="status"
          class="fixed z-[60] border border-gold/50 bg-ink-900 p-4 text-left shadow-2xl shadow-black"
          :class="{ 'hint-above': side === 'top' }"
          :style="{ top: `${place.top}px`, left: `${place.left}px`, width: `${place.width}px` }"
        >
          <span
            class="absolute h-3 w-3 rotate-45 border-gold/50 bg-ink-900"
            :class="side === 'top' ? '-bottom-1.5 border-b border-r' : '-top-1.5 border-l border-t'"
            :style="{ left: `${place.arrow - 6}px` }"
            aria-hidden="true"
          />
          <p class="text-sm leading-relaxed text-parchment">{{ text }}</p>
          <div class="mt-3 flex items-center gap-4">
            <button type="button" class="btn-primary px-3 py-1 text-sm" @click.stop="hints.done(id)">Понятно</button>
            <button type="button" class="text-xs text-parchment-faint transition hover:text-parchment" @click.stop="hints.doneAll()">Больше не показывать</button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import type { HintId } from '~/composables/useHints'

const props = withDefaults(defineProps<{ id: HintId; text: string; side?: 'top' | 'bottom'; align?: 'start' | 'center' | 'end' }>(), {
  side: 'bottom', align: 'start',
})

const GAP = 12
const EDGE = 16 // the page's side gutter
const hints = useHints()
const root = ref<HTMLElement>()
const due = computed(() => hints.current.value === props.id)
// Opens once it has stayed next in line for a moment: while a page appears its elements report in one by one,
// and a header hint shouldn't flash before the page's own takes its place
const open = ref(false)
let settle: ReturnType<typeof setTimeout> | undefined
watch(due, (now) => {
  clearTimeout(settle)
  if (!now) open.value = false
  else settle = setTimeout(() => (open.value = due.value), 250)
})
const place = ref<{ top: number; left: number; width: number; arrow: number } | null>(null)

/** Next to the element, kept inside the screen; the arrow points at the element wherever the bubble had to move */
function measure() {
  const r = root.value?.getBoundingClientRect()
  if (!r) return
  const vw = document.documentElement.clientWidth
  const width = Math.min(288, vw - 2 * EDGE)
  const anchor = props.align === 'start' ? r.left + 20 : props.align === 'end' ? r.right - 20 : r.left + r.width / 2
  const wanted = props.align === 'start' ? r.left : props.align === 'end' ? r.right - width : anchor - width / 2
  const left = Math.max(EDGE, Math.min(wanted, vw - EDGE - width))
  place.value = {
    top: props.side === 'top' ? r.top - GAP : r.bottom + GAP,
    left,
    width,
    arrow: Math.max(14, Math.min(anchor - left, width - 14)),
  }
}

let frame = 0
const follow = () => {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(measure)
}
watch(open, (now) => {
  if (now) {
    measure()
    addEventListener('scroll', follow, { passive: true, capture: true })
    addEventListener('resize', follow, { passive: true })
  } else {
    removeEventListener('scroll', follow, { capture: true })
    removeEventListener('resize', follow)
  }
})

// A hint waits until its element is on the screen (a form's lower part, the phone and desktop layouts differ),
// and appears a moment after the page, not while it is still settling
let observer: IntersectionObserver | undefined
let timer: ReturnType<typeof setTimeout> | undefined
onMounted(() => {
  timer = setTimeout(() => {
    observer = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && root.value?.getClientRects().length) hints.show(props.id)
      else hints.hide(props.id)
    })
    if (root.value) observer.observe(root.value)
  }, 700)
})
onBeforeUnmount(() => {
  clearTimeout(timer)
  clearTimeout(settle)
  observer?.disconnect()
  cancelAnimationFrame(frame)
  removeEventListener('scroll', follow, { capture: true })
  removeEventListener('resize', follow)
  hints.hide(props.id)
})
</script>

<style scoped>
.hint-above { transform: translateY(-100%); }
.hint-enter-active { transition: opacity .25s ease; }
.hint-leave-active { transition: opacity .15s ease; }
.hint-enter-from, .hint-leave-to { opacity: 0; }
</style>
