<template>
  <Teleport to="body">
    <Transition name="palette">
      <div v-if="state.open" class="fixed inset-0 z-[60] flex items-start justify-center bg-ink-950/80 px-4 pt-[12vh] backdrop-blur-sm" @click.self="close">
        <div class="frame w-full max-w-2xl">
          <div class="frame-inner bg-ink-900">
            <div class="flex items-center gap-3 border-b border-gold/15 px-5">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" class="text-gold"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
              <input
                ref="input"
                v-model="q"
                class="w-full bg-transparent py-4 font-elegant text-2xl italic text-parchment outline-none placeholder:text-parchment-faint/60"
                placeholder="Слова из текста, название, композитор…"
                @keydown.down.prevent="move(1)"
                @keydown.up.prevent="move(-1)"
                @keydown.enter.prevent="items[active] ? go(items[active]) : showAll()"
                @keydown.esc="close"
              >
              <kbd class="font-mono text-xs text-parchment-faint">Esc</kbd>
            </div>

            <div class="max-h-[55vh] overflow-y-auto py-2">
              <p v-if="!q.trim()" class="px-5 py-6 text-center font-elegant text-lg italic text-parchment-faint">
                Ищите по словам: в текстах записей, описаниях опусов, названиях и именах
              </p>
              <p v-else-if="!loading && !items.length" class="px-5 py-6 text-center font-elegant text-lg italic text-parchment-faint">
                Ничего не нашлось
              </p>
              <template v-for="group in groups" :key="group.title">
                <p class="eyebrow px-5 pb-1 pt-3 text-xs">{{ group.title }}</p>
                <button
                  v-for="item in group.items"
                  :key="item.to"
                  type="button"
                  class="flex w-full items-center gap-3 px-5 py-2 text-left transition"
                  :class="items[active] === item ? 'bg-gold/15 text-gold-light' : 'text-parchment hover:bg-gold/5'"
                  @mouseenter="active = items.indexOf(item)"
                  @click="go(item)"
                >
                  <UserAvatar v-if="item.user" :user="item.user" :size="28" />
                  <span v-else class="w-7 text-center font-display text-gold">{{ item.icon }}</span>
                  <span class="min-w-0 flex-1">
                    <span class="block truncate font-display">{{ item.title }}</span>
                    <span v-if="item.snippet" class="line-clamp-2 block text-sm text-parchment-muted"><HighlightText :text="item.snippet" :words="words" /></span>
                    <span v-if="item.hint" class="block truncate text-sm italic text-parchment-faint">{{ item.hint }}</span>
                  </span>
                </button>
              </template>
              <button
                v-if="items.length"
                type="button"
                class="mt-1 w-full border-t border-gold/10 px-5 pb-1 pt-3 text-left font-caps text-sm font-semibold tracking-[0.15em] text-gold transition hover:text-gold-light"
                @click="showAll"
              >
                Все результаты →
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { SearchItem as Item } from '~/composables/useLiveSearch'

const state = useSearchPalette()
const { q, loading, groups, words, items, active, move } = useLiveSearch(5)
const input = ref<HTMLInputElement>()
const close = () => {
  state.open = false
}
/** The /search page: every match, not only the first few */
const showAll = () => {
  const query = q.value.trim()
  if (!query) return
  close()
  navigateTo({ path: '/search', query: { q: query } })
}
const go = (item?: Item) => {
  if (!item) return
  close()
  q.value = ''
  navigateTo(item.to)
}

watch(() => state.open, async (open) => {
  if (open) {
    await nextTick()
    input.value?.focus()
  }
})

const onKey = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    state.open = !state.open
  } else if (e.key === 'Escape' && state.open) {
    close()
  }
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.palette-enter-active, .palette-leave-active { transition: opacity .25s; }
.palette-enter-active .frame, .palette-leave-active .frame { transition: transform .25s; }
.palette-enter-from, .palette-leave-to { opacity: 0; }
.palette-enter-from .frame { transform: translateY(-12px) scale(.98); }
</style>
