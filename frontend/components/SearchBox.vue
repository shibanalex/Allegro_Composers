<template>
  <!-- A search field with results as you type; Enter opens every result on /search -->
  <div ref="root" class="relative">
    <form role="search" class="relative" @submit.prevent="submit">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-gold/70"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
      <input
        v-model="q"
        type="search"
        class="field !pl-12 font-elegant text-lg"
        :placeholder="placeholder"
        aria-label="Поиск по сайту"
        autocomplete="off"
        @focus="open = true"
        @keydown.down.prevent="open = true; move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.esc="open = false"
        @keydown.enter.prevent="items[active] && open ? go(items[active]) : submit()"
      >
    </form>

    <div v-if="open && q.trim()" class="absolute left-0 right-0 top-full z-40 mt-1 max-h-[60vh] overflow-y-auto border border-gold/25 bg-ink-900/95 py-2 shadow-2xl shadow-black backdrop-blur">
      <p v-if="loading && !items.length" class="px-4 py-3 font-elegant italic text-parchment-faint">Ищу…</p>
      <p v-else-if="!items.length" class="px-4 py-3 font-elegant italic text-parchment-faint">Ничего не нашлось</p>
      <template v-for="group in groups" :key="group.title">
        <p class="eyebrow px-4 pb-1 pt-3 text-xs">{{ group.title }}</p>
        <NuxtLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-4 py-2 transition"
          :class="items[active] === item ? 'bg-gold/15 text-gold-light' : 'text-parchment hover:bg-gold/5'"
          @mouseenter="active = items.indexOf(item)"
          @click="close"
        >
          <UserAvatar v-if="item.user" :user="item.user" :size="28" />
          <span v-else class="w-7 text-center font-display text-gold">{{ item.icon }}</span>
          <span class="min-w-0 flex-1">
            <span class="block truncate font-display">{{ item.title }}</span>
            <span v-if="item.snippet" class="line-clamp-2 block text-sm text-parchment-muted"><HighlightText :text="item.snippet" :words="words" /></span>
            <span v-if="item.hint" class="block truncate text-sm italic text-parchment-faint">{{ item.hint }}</span>
          </span>
        </NuxtLink>
      </template>
      <button v-if="items.length" type="button" class="mt-1 w-full border-t border-gold/10 px-4 pb-1 pt-3 text-left font-caps text-sm font-semibold tracking-[0.15em] text-gold transition hover:text-gold-light" @click="submit">
        Все результаты →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SearchItem } from '~/composables/useLiveSearch'

withDefaults(defineProps<{ placeholder?: string }>(), { placeholder: 'Поиск: сочинения, участники, записи, инструменты…' })

const { q, loading, groups, words, items, active, move } = useLiveSearch(5)
const open = ref(false)
const root = ref<HTMLElement>()

function close() {
  open.value = false
  q.value = ''
}
function go(item: SearchItem) {
  close()
  navigateTo(item.to)
}
function submit() {
  const query = q.value.trim()
  if (!query) return
  close()
  navigateTo({ path: '/search', query: { q: query } })
}

const onDocClick = (e: MouseEvent) => {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>
