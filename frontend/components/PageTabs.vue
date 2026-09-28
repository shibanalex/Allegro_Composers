<template>
  <!-- A folder with index dividers: the tab labels stick out above the sheet;
       switching is a quick, quiet cross-fade (no page flipping). -->
  <div class="folder">
    <nav class="folder-tabs" :class="{ dense: tabs.length > 5 }" role="tablist">
      <button
        v-for="(tab, i) in tabs"
        :key="tab.id"
        type="button"
        role="tab"
        class="folder-tab"
        :class="{ active: tab.id === current }"
        :style="{ zIndex: tab.id === current ? 30 : 20 - i }"
        :aria-selected="tab.id === current"
        @click="select(tab.id)"
      >
        <span class="folder-tab-label">{{ tab.label }}</span>
        <span v-if="tab.count != null" class="folder-tab-count">{{ tab.count }}</span>
      </button>
    </nav>

    <div class="folder-body">
      <Transition :css="false" @enter="enter" @leave="leave">
        <div :key="current" class="folder-sheet">
          <!-- A tab's content may load its own data (catalogue, performances): wait for it here -->
          <Suspense>
            <div><slot :name="current" /></div>
            <template #fallback>
              <p class="py-16 text-center font-elegant text-xl italic text-parchment-faint">Загрузка…</p>
            </template>
          </Suspense>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  tabs: { id: string; label: string; count?: number | null }[]
  /** Query parameter that keeps the tab in the URL (shareable, survives reload) */
  query?: string
}>()

const route = useRoute()
const key = props.query ?? 'tab'

const valid = (value: unknown) => (props.tabs.some((t) => t.id === value) ? (value as string) : props.tabs[0].id)
const index = (id: string) => props.tabs.findIndex((t) => t.id === id)

const current = ref(valid(route.query[key]))
let distance = 1 // signed number of bookmarks travelled by the last switch

const select = (id: string) => {
  if (id === current.value) return
  distance = index(id) - index(current.value)
  current.value = id
  // Update the address without a router navigation: no scroll jump, no re-render of the page
  const url = new URL(window.location.href)
  if (id === props.tabs[0].id) url.searchParams.delete(key)
  else url.searchParams.set(key, id)
  window.history.replaceState(window.history.state, '', url)
}

// Links such as /@user?tab=collections while already on the page
watch(() => route.query[key], (value) => select(valid(value)))

// ---------------------------------------------------------------- quick, quiet switch

const reduced = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches
const OUT_MS = 110
const IN_MS = 190

/** The old sheet fades out on top, without affecting the layout */
function leave(el: Element, done: () => void) {
  const sheet = el as HTMLElement
  if (reduced()) return done()
  Object.assign(sheet.style, { position: 'absolute', inset: '0 0 auto 0', zIndex: '2', pointerEvents: 'none' })
  sheet.animate([{ opacity: 1 }, { opacity: 0 }], { duration: OUT_MS, easing: 'ease-out', fill: 'forwards' }).onfinish = done
}

/** The new sheet fades in with a barely noticeable lift, a direction hint from where the tab is */
function enter(el: Element, done: () => void) {
  if (reduced()) return done()
  const shift = Math.sign(distance) * 6
  ;(el as HTMLElement).animate(
    [
      { opacity: 0, transform: `translate(${shift}px, 4px)` },
      { opacity: 1, transform: 'translate(0, 0)' },
    ],
    { duration: IN_MS, delay: OUT_MS * 0.5, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'backwards' },
  ).onfinish = done
}
</script>
