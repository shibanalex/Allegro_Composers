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
                placeholder="Композитор, опус, инструмент…"
                @keydown.down.prevent="move(1)"
                @keydown.up.prevent="move(-1)"
                @keydown.enter.prevent="go(items[active])"
                @keydown.esc="close"
              >
              <kbd class="font-mono text-xs text-parchment-faint">Esc</kbd>
            </div>

            <div class="max-h-[55vh] overflow-y-auto py-2">
              <p v-if="!q.trim()" class="px-5 py-6 text-center font-elegant text-lg italic text-parchment-faint">
                Ищите по композиторам, названиям опусов и инструментам
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
                    <span v-if="item.hint" class="block truncate text-sm italic text-parchment-faint">{{ item.hint }}</span>
                  </span>
                </button>
              </template>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { UserBrief } from '~/utils/types'

interface Item { to: string; title: string; hint?: string | null; icon?: string; user?: UserBrief }

const state = useSearchPalette()
const api = useApi()
const q = ref('')
const loading = ref(false)
const active = ref(0)
const input = ref<HTMLInputElement>()
const groups = ref<{ title: string; items: Item[] }[]>([])
const items = computed(() => groups.value.flatMap((g) => g.items))

let timer: ReturnType<typeof setTimeout> | undefined
let requestId = 0
watch(q, (value) => {
  clearTimeout(timer)
  if (!value.trim()) return (groups.value = [])
  timer = setTimeout(async () => {
    const id = ++requestId
    loading.value = true
    try {
      const r = await api<any>('/api/search', { params: { q: value.trim(), limit: 5 } })
      if (id !== requestId) return
      groups.value = [
        { title: 'Композиторы', items: r.composers.map((u: any) => ({ to: `/@${u.username}`, title: u.display_name, hint: u.pseudonym || u.bio, user: u })) },
        { title: 'Опусы', items: r.opuses.map((o: any) => ({ to: `/opus/${o.slug}`, title: o.title, hint: [o.subtitle, o.author.display_name].filter(Boolean).join(' · '), icon: '♪' })) },
        { title: 'Инструменты и теги', items: r.tags.map((t: string) => ({ to: `/library?tag=${encodeURIComponent(t)}`, title: t, hint: 'все опусы в библиотеке', icon: '#' })) },
        { title: 'Публикации', items: r.posts.map((p: any) => ({ to: `/posts/${p.slug}`, title: p.title, hint: `${POST_KINDS[p.kind]} · ${p.author.display_name}`, icon: '¶' })) },
      ].filter((g) => g.items.length)
      active.value = 0
    } finally {
      if (id === requestId) loading.value = false
    }
  }, 180)
})

const move = (d: number) => {
  if (items.value.length) active.value = (active.value + d + items.value.length) % items.value.length
}
const close = () => {
  state.open = false
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
