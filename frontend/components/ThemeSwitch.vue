<template>
  <!-- The style of the whole site for this visitor: four eras, remembered in this browser -->
  <div ref="root" class="relative">
    <button
      type="button"
      class="flex h-9 w-9 items-center justify-center border border-gold/20 text-lg text-gold transition hover:border-gold/60 hover:text-gold-light"
      :aria-expanded="open"
      aria-label="Стиль сайта"
      title="Стиль сайта"
      @click="open = !open"
    >
      {{ ICONS[theme] }}
    </button>
    <Transition name="drop">
      <div v-if="open" class="absolute right-0 top-full z-50 mt-2 w-72 border border-gold/25 bg-ink-900/95 py-2 shadow-2xl shadow-black backdrop-blur">
        <p class="px-4 pb-2 pt-1 font-caps text-xs font-semibold tracking-[0.2em] text-parchment-faint">Стиль сайта</p>
        <button
          v-for="t in themes"
          :key="t"
          type="button"
          class="flex w-full items-baseline gap-3 px-4 py-2 text-left transition hover:bg-gold/10"
          :class="t === theme ? 'text-gold-light' : 'text-parchment'"
          :aria-pressed="t === theme"
          @click="pick(t)"
        >
          <span class="w-5 text-center text-gold">{{ ICONS[t] }}</span>
          <span class="font-elegant text-lg">{{ HALL_THEMES[t].label }}</span>
          <span v-if="t === theme" class="ml-auto text-sm">✓</span>
        </button>
        <button v-if="user && chosen" type="button" class="mt-1 w-full border-t border-gold/10 px-4 pb-1 pt-2 text-left text-sm text-parchment-faint transition hover:text-gold-light" @click="pick(null)">
          Как в моём зале
        </button>
        <p class="px-4 pt-2 text-xs leading-snug text-parchment-faint">Залы участников показываются в стиле, который выбрал их владелец.</p>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import type { HallTheme } from '~/utils/types'

const ICONS: Record<HallTheme, string> = { baroque: '♛', romantic: '❦', modern: '❀', avantgarde: '◼' }

const { user } = useAuth()
const { themes, theme, chosen, setTheme } = useSiteTheme()
const open = ref(false)
const root = ref<HTMLElement>()

function pick(t: HallTheme | null) {
  setTheme(t)
  open.value = false
}

const onDocClick = (e: MouseEvent) => {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>
