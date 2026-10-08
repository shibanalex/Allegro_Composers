<template>
  <!-- The community chat: the conversation live through Centrifugo (WebSocket); everyone reads, members write -->
  <section class="flex min-h-0 flex-col border border-gold/15 bg-ink-950/60" aria-label="Чат сообщества">
    <header class="flex items-center gap-3 border-b border-gold/15 px-4 py-3">
      <h2 class="font-caps text-sm font-semibold tracking-[0.2em] text-gold">Чат сообщества</h2>
      <span class="ml-auto flex items-center gap-1.5 text-xs text-parchment-faint" :title="live ? 'Сообщения приходят сразу' : 'Соединение восстанавливается — сообщения подгружаются раз в несколько секунд'">
        <span class="h-2 w-2 rounded-full" :class="live ? 'bg-emerald-400/80' : 'bg-parchment-faint/50'" />
        {{ live ? 'в реальном времени' : 'подключаюсь…' }}
      </span>
      <slot name="close" />
    </header>

    <!-- The conversation, the newest at the bottom -->
    <div ref="scroller" class="thin-scroll relative min-h-0 flex-1 overflow-y-auto px-3 py-3 sm:px-4" @scroll.passive="onScroll">
      <div v-if="olderFrom" class="mb-3 text-center">
        <button type="button" class="btn-ghost text-sm" :disabled="loadingOlder" @click="loadOlder">{{ loadingOlder ? 'Загружаю…' : 'Раньше' }}</button>
      </div>
      <p v-if="!loaded" class="py-10 text-center font-elegant italic text-parchment-faint">Загружаю разговор…</p>
      <p v-else-if="!messages.length" class="py-10 text-center font-elegant text-lg italic text-parchment-faint">Здесь пока тихо. Начните разговор.</p>

      <template v-for="(m, i) in messages" :key="m.id">
        <p v-if="newDay(i)" class="my-3 text-center text-xs uppercase tracking-[0.2em] text-parchment-faint">{{ dayLabel(m.created_at) }}</p>
        <article
          :id="`m-${m.id}`"
          class="group relative flex gap-3 rounded px-2 py-0.5 transition-colors"
          :class="[startsGroup(i) ? 'mt-3' : '', mentionsMe(m) ? 'bg-gold/10' : 'hover:bg-ink-900/60', flash === m.id ? 'ring-1 ring-gold/60' : '']"
        >
          <NuxtLink v-if="startsGroup(i)" :to="`/@${m.author.username}`" class="mt-0.5 shrink-0"><UserAvatar :user="m.author" :size="34" /></NuxtLink>
          <span v-else class="w-[34px] shrink-0" />
          <div class="min-w-0 flex-1">
            <p v-if="startsGroup(i)" class="flex items-baseline gap-2">
              <NuxtLink :to="`/@${m.author.username}`" class="truncate font-display italic text-gold-light transition hover:text-gold">{{ m.author.display_name }}</NuxtLink>
              <time class="shrink-0 text-xs text-parchment-faint" :datetime="m.created_at">{{ formatClock(m.created_at) }}</time>
            </p>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <p class="chat-text break-words text-[0.95rem] leading-snug text-parchment" v-html="renderChatText(m.text, user?.username)" />
          </div>
          <button
            v-if="canDelete(m)"
            type="button"
            class="absolute right-1 top-0.5 hidden px-1 text-sm text-parchment-faint transition hover:text-red-300 group-hover:block group-focus-within:block"
            aria-label="Удалить сообщение"
            @click="remove(m)"
          >✕</button>
        </article>
      </template>
    </div>

    <!-- Someone wrote while the reader was scrolled up -->
    <div v-if="unseen" class="relative">
      <button type="button" class="btn-primary absolute -top-12 left-1/2 -translate-x-1/2 px-4 py-1 text-sm shadow-lg" @click="toBottom(true)">↓ Новые сообщения</button>
    </div>

    <!-- Writing -->
    <form v-if="user && can('chat')" class="relative border-t border-gold/15 p-3" @submit.prevent="send">
      <ul v-if="suggestions.length" class="absolute bottom-full left-3 right-3 mb-1 border border-gold/25 bg-ink-900/95 py-1 shadow-2xl shadow-black backdrop-blur" role="listbox">
        <li v-for="(s, i) in suggestions" :key="s.id">
          <button
            type="button"
            class="flex w-full items-center gap-3 px-3 py-1.5 text-left transition"
            :class="i === picked ? 'bg-gold/15 text-gold-light' : 'text-parchment hover:bg-gold/10'"
            role="option"
            :aria-selected="i === picked"
            @mousedown.prevent="pick(s)"
          >
            <UserAvatar :user="s" :size="26" />
            <span class="truncate font-display italic">{{ s.display_name }}</span>
            <span class="truncate text-sm text-parchment-faint">@{{ s.username }}</span>
          </button>
        </li>
      </ul>
      <div class="flex items-end gap-2">
        <textarea
          ref="field"
          v-model="draft"
          rows="1"
          maxlength="2000"
          class="field max-h-40 min-h-[2.75rem] flex-1 resize-none text-base leading-snug"
          placeholder="Сообщение… @имя — упомянуть"
          aria-label="Сообщение в чат"
          @input="onType"
          @keydown="onKey"
          @click="lookForMention"
        />
        <button type="submit" class="btn-primary h-11 shrink-0 px-4" :disabled="sending || !draft.trim()" aria-label="Отправить">➤</button>
      </div>
      <p v-if="error" class="mt-1 text-sm text-red-300">{{ error }}</p>
    </form>
    <p v-else-if="user" class="border-t border-gold/15 p-4 text-center text-sm text-parchment-faint">Писать в чат вам сейчас нельзя.</p>
    <p v-else class="border-t border-gold/15 p-4 text-center font-elegant text-lg italic text-parchment-muted">
      <NuxtLink :to="`/login?next=${encodeURIComponent(route.fullPath)}`" class="link">Войдите</NuxtLink>
      или <NuxtLink :to="`/register?next=${encodeURIComponent(route.fullPath)}`" class="link">откройте свой зал</NuxtLink>, чтобы писать.
    </p>
  </section>
</template>

<script setup lang="ts">
import type { Centrifuge, Subscription } from 'centrifuge'
import type { UserBrief } from '~/utils/types'

interface Message { id: string; text: string; author: UserBrief; created_at: string }
interface Page { items: Message[]; next_before: string | null }
interface Connection { url: string; token: string; channel: string }

const api = useApi()
const route = useRoute()
const { user, can } = useAuth()

const messages = ref<Message[]>([])
const loaded = ref(false)
const olderFrom = ref<string | null>(null)
const loadingOlder = ref(false)
const live = ref(false)
const scroller = ref<HTMLElement>()
const unseen = ref(false)
const flash = ref<string | null>(null)

// ---------------------------------------------------------------- the history and new messages

function merge(incoming: Message[]) {
  const known = new Set(messages.value.map((m) => m.id))
  const fresh = incoming.filter((m) => !known.has(m.id))
  if (!fresh.length) return false
  messages.value = [...messages.value, ...fresh].sort((a, b) => a.created_at.localeCompare(b.created_at))
  return true
}

async function loadLatest() {
  const page = await api<Page>('/api/chat/messages', { params: { limit: 50 } })
  if (!loaded.value) olderFrom.value = page.next_before
  const nearBottom = atBottom()
  const changed = merge(page.items)
  loaded.value = true
  if (changed) settle(nearBottom)
}

async function loadOlder() {
  if (!olderFrom.value) return
  loadingOlder.value = true
  const el = scroller.value!
  const before = el.scrollHeight - el.scrollTop
  try {
    const page = await api<Page>('/api/chat/messages', { params: { limit: 50, before: olderFrom.value } })
    merge(page.items)
    olderFrom.value = page.next_before
    await nextTick()
    el.scrollTop = el.scrollHeight - before // the reader stays where they were
  } finally {
    loadingOlder.value = false
  }
}

/** After new messages: follow them if the reader was at the bottom, otherwise offer «↓ Новые сообщения» */
async function settle(follow: boolean) {
  await nextTick()
  if (follow) toBottom(false)
  else unseen.value = true
}

function atBottom() {
  const el = scroller.value
  return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 80
}
function toBottom(smooth: boolean) {
  const el = scroller.value
  if (el) el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
  unseen.value = false
}
function onScroll() {
  if (atBottom()) unseen.value = false
}

// ---------------------------------------------------------------- live: Centrifugo

let centrifuge: Centrifuge | null = null
let subscription: Subscription | null = null
let polling: ReturnType<typeof setInterval> | undefined

async function connect() {
  disconnect()
  try {
    const { Centrifuge } = await import('centrifuge')
    const pass = await api<Connection>('/api/chat/connection')
    // On the site the gateway (Caddy) hands /connection to Centrifugo; in development it runs on its own port
    const host = import.meta.dev ? `${location.hostname}:8001` : location.host
    const address = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${host}${pass.url}`
    centrifuge = new Centrifuge(address, {
      token: pass.token,
      getToken: async () => (await api<Connection>('/api/chat/connection')).token,
    })
    subscription = centrifuge.newSubscription(pass.channel)
    subscription.on('publication', (ctx) => onEvent(ctx.data))
    // (re)joined: whatever was said while the connection was down is fetched
    subscription.on('subscribed', () => {
      live.value = true
      loadLatest().catch(() => {})
    })
    subscription.on('unsubscribed', () => (live.value = false))
    centrifuge.on('disconnected', () => (live.value = false))
    centrifuge.on('connecting', () => (live.value = false))
    subscription.subscribe()
    centrifuge.connect()
  } catch {
    live.value = false
  }
}

function disconnect() {
  subscription?.unsubscribe()
  subscription?.removeAllListeners()
  centrifuge?.disconnect()
  subscription = null
  centrifuge = null
  live.value = false
}

function onEvent(data: { type: string; message?: Message; id?: string }) {
  if (data.type === 'message' && data.message) {
    const follow = atBottom() || data.message.author.id === user.value?.id
    if (merge([data.message])) settle(follow)
  } else if (data.type === 'deleted' && data.id) {
    messages.value = messages.value.filter((m) => m.id !== data.id)
  }
}

// ---------------------------------------------------------------- writing

const draft = ref('')
const sending = ref(false)
const error = ref('')
const field = ref<HTMLTextAreaElement>()

async function send() {
  const text = draft.value.trim()
  if (!text || sending.value) return
  sending.value = true
  error.value = ''
  try {
    const message = await api<Message>('/api/chat/messages', { method: 'POST', body: { text } })
    draft.value = ''
    suggestions.value = []
    grow()
    merge([message]) // at once, without waiting for the channel
    settle(true)
  } catch (e) {
    error.value = apiError(e)
  } finally {
    sending.value = false
    field.value?.focus()
  }
}

async function remove(m: Message) {
  if (!confirm('Удалить сообщение?')) return
  try {
    await api(`/api/chat/messages/${m.id}`, { method: 'DELETE' })
    messages.value = messages.value.filter((x) => x.id !== m.id)
  } catch (e) {
    alert(apiError(e))
  }
}

const canDelete = (m: Message) => !!user.value && (m.author.id === user.value.id || can('moderate'))
const mentionsMe = (m: Message) => mentions(m.text, user.value?.username)

function grow() {
  const el = field.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}

// ---------------------------------------------------------------- @mentions: suggestions as one types

const suggestions = ref<UserBrief[]>([])
const picked = ref(0)
let asking: ReturnType<typeof setTimeout> | undefined

/** The «@word» just before the cursor, if the cursor is in one */
function mentionAtCursor() {
  const el = field.value
  if (!el) return null
  const upto = draft.value.slice(0, el.selectionStart)
  const m = upto.match(/(?:^|[\s(])@([\p{L}\d._-]{0,30})$/u)
  return m ? { word: m[1], start: upto.length - m[1].length - 1 } : null
}

function lookForMention() {
  clearTimeout(asking)
  const found = mentionAtCursor()
  if (!found) return void (suggestions.value = [])
  asking = setTimeout(async () => {
    const page = await api<{ items: UserBrief[] }>('/api/users', { params: { q: found.word, limit: 6 } }).catch(() => null)
    suggestions.value = (page?.items || []).filter((u) => u.id !== user.value?.id)
    picked.value = 0
  }, found.word ? 200 : 0)
}

function pick(s: UserBrief) {
  const found = mentionAtCursor()
  const el = field.value
  if (!found || !el) return
  const before = draft.value.slice(0, found.start)
  const after = draft.value.slice(el.selectionStart)
  draft.value = `${before}@${s.username} ${after.replace(/^\S*/, '')}`
  suggestions.value = []
  nextTick(() => {
    const at = before.length + s.username.length + 2
    el.focus()
    el.setSelectionRange(at, at)
  })
}

function onType() {
  grow()
  lookForMention()
}

function onKey(e: KeyboardEvent) {
  if (suggestions.value.length) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const n = suggestions.value.length
      picked.value = (picked.value + (e.key === 'ArrowDown' ? 1 : n - 1)) % n
      return
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault()
      pick(suggestions.value[picked.value])
      return
    }
    if (e.key === 'Escape') return void (suggestions.value = [])
  }
  // Enter sends, Shift+Enter starts a new line (on a phone the keyboard's Enter is a new line)
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && !matchMedia('(pointer: coarse)').matches) {
    e.preventDefault()
    send()
  }
}

// ---------------------------------------------------------------- days

const sameDay = (a: string, b: string) => formatDate(a) === formatDate(b)
const newDay = (i: number) => i === 0 || !sameDay(messages.value[i - 1].created_at, messages.value[i].created_at)
/** A new author, a new day or five minutes of silence start a new group (avatar and name again) */
function startsGroup(i: number) {
  if (i === 0 || newDay(i)) return true
  const prev = messages.value[i - 1]
  const cur = messages.value[i]
  return prev.author.id !== cur.author.id || Date.parse(cur.created_at) - Date.parse(prev.created_at) > 5 * 60_000
}
function dayLabel(iso: string) {
  const now = new Date().toISOString()
  if (sameDay(iso, now)) return 'Сегодня'
  if (sameDay(iso, new Date(Date.now() - 86_400_000).toISOString())) return 'Вчера'
  return formatDate(iso)
}

// ---------------------------------------------------------------- the life of the component

onMounted(async () => {
  await loadLatest().catch(() => (loaded.value = true))
  await nextTick()
  // a notification «упомянул(а) вас» leads to /?feed=chat#m-<id>: that message, lit for a moment
  const target = route.hash.startsWith('#m-') ? document.getElementById(route.hash.slice(1)) : null
  if (target) {
    target.scrollIntoView({ block: 'center' })
    flash.value = route.hash.slice(3)
    setTimeout(() => (flash.value = null), 2500)
  } else {
    toBottom(false)
  }
  connect()
  // without the live channel the conversation still moves, only slower
  polling = setInterval(() => {
    if (!live.value && document.visibilityState === 'visible') loadLatest().catch(() => {})
  }, 10_000)
})
// signing in or out changes who is listening: a new pass
watch(() => user.value?.id, () => connect())
onBeforeUnmount(() => {
  clearInterval(polling)
  clearTimeout(asking)
  disconnect()
})
</script>

<style scoped>
.chat-text :deep(.chat-mention) { color: rgb(var(--c-gold-light)); }
.chat-text :deep(.chat-mention:hover) { text-decoration: underline; }
.chat-text :deep(.chat-mention.is-me) { background: rgb(var(--c-gold) / 0.2); padding: 0 0.2em; border-radius: 2px; }
</style>
