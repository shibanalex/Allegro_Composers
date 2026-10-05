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
          :style="{ top: `${place.top}px`, left: `${place.left}px`, width: `${place.width}px` }"
        >
          <span
            v-if="place.arrow !== null"
            class="absolute h-3 w-3 rotate-45 border-gold/50 bg-ink-900"
            :class="place.side === 'top' ? '-bottom-1.5 border-b border-r' : '-top-1.5 border-l border-t'"
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
const bubble = ref<HTMLElement>()
// side: where the bubble ended up (it moves to the other side when there is no room); arrow: null when it can't point
const place = ref<{ top: number; left: number; width: number; side: 'top' | 'bottom'; arrow: number | null } | null>(null)

/** The part of the screen a bubble may use: below the sticky site header, inside what a phone actually shows */
function screen() {
  const view = window.visualViewport
  const width = Math.min(document.documentElement.clientWidth, view?.width ?? Infinity)
  const height = view?.height ?? window.innerHeight
  const header = document.querySelector('header')?.getBoundingClientRect().bottom ?? 0 // the site header comes first
  return { width, height, top: Math.max(header, 0) + 8 }
}

/** Next to the element and wholly on the screen; the arrow points at the element when the bubble is beside it */
function measure() {
  const r = root.value?.getBoundingClientRect()
  if (!r) return
  const s = screen()
  const width = Math.min(288, s.width - 2 * EDGE)
  const height = bubble.value?.offsetHeight || 170
  const anchor = props.align === 'start' ? r.left + 20 : props.align === 'end' ? r.right - 20 : r.left + r.width / 2
  const wanted = props.align === 'start' ? r.left : props.align === 'end' ? r.right - width : anchor - width / 2
  const left = Math.max(EDGE, Math.min(wanted, s.width - EDGE - width))

  const below = r.bottom + GAP
  const above = r.top - GAP - height
  const fits = { bottom: below + height <= s.height - EDGE, top: above >= s.top }
  const other = props.side === 'top' ? 'bottom' : 'top'
  const side = fits[props.side] || !fits[other] ? props.side : other
  const wantedTop = side === 'top' ? above : below
  const top = Math.max(s.top, Math.min(wantedTop, s.height - EDGE - height))
  place.value = {
    top, left, width, side,
    arrow: top === wantedTop ? Math.max(14, Math.min(anchor - left, width - 14)) : null,
  }
}

let frame = 0
const follow = () => {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(measure)
}
function stopFollowing() {
  removeEventListener('scroll', follow, { capture: true })
  removeEventListener('resize', follow)
  window.visualViewport?.removeEventListener('resize', follow)
}
watch(open, async (now) => {
  if (now) {
    measure()
    await nextTick()
    measure() // again with the bubble's real height
    addEventListener('scroll', follow, { passive: true, capture: true })
    addEventListener('resize', follow, { passive: true })
    window.visualViewport?.addEventListener('resize', follow, { passive: true })
  } else {
    stopFollowing()
  }
})

// A hint waits until its element is well on the screen, not just its edge peeping in (a form's lower part,
// the phone and desktop layouts differ), and appears a moment after the page, not while it is still settling
let observer: IntersectionObserver | undefined
let timer: ReturnType<typeof setTimeout> | undefined
onMounted(() => {
  timer = setTimeout(() => {
    // below the site header and above the lowest fifth of the screen (the header's own buttons: the whole screen)
    const inHeader = !!root.value?.closest('header')
    observer = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && root.value?.getClientRects().length) hints.show(props.id)
      else hints.hide(props.id)
    }, { rootMargin: inHeader ? '0px' : '-80px 0px -20% 0px' })
    if (root.value) observer.observe(root.value)
  }, 700)
})
onBeforeUnmount(() => {
  clearTimeout(timer)
  clearTimeout(settle)
  observer?.disconnect()
  cancelAnimationFrame(frame)
  stopFollowing()
  hints.hide(props.id)
})
</script>

<style scoped>
.hint-enter-active { transition: opacity .25s ease; }
.hint-leave-active { transition: opacity .15s ease; }
.hint-enter-from, .hint-leave-to { opacity: 0; }
</style>
