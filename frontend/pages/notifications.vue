<template>
  <div class="mx-auto max-w-3xl">
    <PageHeader eyebrow="Что нового в залах" title="Уведомления" />

    <!-- The list -->
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <p class="font-elegant text-lg italic text-parchment-muted">
        {{ unread ? `${unread} ${plural(unread, 'новое', 'новых', 'новых')}` : 'Всё прочитано' }}
      </p>
      <button v-if="unread" type="button" class="btn-secondary px-4 py-1.5 text-sm" @click="readAll">Отметить всё прочитанным</button>
    </div>

    <EmptyState v-if="!items.length">Пока ничего — здесь появятся новые публикации участников</EmptyState>
    <ul v-if="items.length" class="divide-y divide-gold/10 border-y border-gold/10">
      <li v-for="n in items" :key="n.id">
        <NuxtLink :to="n.url" class="flex items-start gap-4 px-2 py-4 transition hover:bg-gold/5" :class="{ 'bg-gold/[0.04]': !n.read_at }" @click="readOne(n)">
          <UserAvatar v-if="n.actor" :user="n.actor" :size="42" />
          <span class="min-w-0 flex-1 leading-snug">
            <span class="block text-parchment-muted">
              <span class="font-display italic text-parchment">{{ n.actor?.display_name || 'Участник' }}</span>
              · {{ KIND_WORDS[n.kind] || 'новая публикация' }}
            </span>
            <span class="block truncate font-display text-lg text-parchment">{{ n.title }}</span>
            <span class="text-sm text-parchment-faint">{{ when(n.created_at) }}</span>
          </span>
          <span v-if="!n.read_at" class="mt-2 h-2.5 w-2.5 shrink-0 rounded-full bg-gold" aria-label="Новое" />
        </NuxtLink>
      </li>
    </ul>
    <div v-if="nextBefore" class="mt-6 text-center">
      <button type="button" class="btn-secondary" :disabled="loading" @click="more">Раньше</button>
    </div>

    <!-- Settings -->
    <section v-if="prefs" class="mt-16 space-y-8 border-t border-gold/15 pt-10">
      <h2 class="text-3xl italic">Настройки</h2>

      <div>
        <p class="field-label">О чём сообщать</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="(label, kind) in KIND_LABELS"
            :key="kind"
            type="button"
            class="chip"
            :class="{ active: prefs.kinds.includes(kind) }"
            :aria-pressed="prefs.kinds.includes(kind)"
            @click="toggleKind(kind)"
          >
            {{ label }}
          </button>
        </div>
      </div>

      <div>
        <p class="field-label">В браузере — даже когда сайт закрыт</p>
        <p v-if="!pushSupported" class="text-sm text-parchment-faint">Этот браузер не умеет показывать уведомления. На iPhone — добавьте сайт на экран «Домой» и откройте его оттуда.</p>
        <div v-else class="flex flex-wrap items-center gap-3">
          <button v-if="!pushOn" type="button" class="btn-primary px-5 py-1.5 text-sm" :disabled="busy" @click="turnPushOn">Включить на этом устройстве</button>
          <button v-else type="button" class="btn-secondary px-5 py-1.5 text-sm" :disabled="busy" @click="turnPushOff">Выключить на этом устройстве</button>
          <span v-if="pushOn" class="text-sm text-gold-light">Включено</span>
          <span v-if="denied" class="text-sm text-red-300">Браузер запретил уведомления — разрешите их в настройках сайта (значок замка у адреса)</span>
        </div>
      </div>

      <div>
        <p class="field-label">Письма на почту</p>
        <div v-if="prefs.email_available" class="flex flex-wrap gap-2">
          <button v-for="(label, mode) in EMAIL_MODES" :key="mode" type="button" class="chip" :class="{ active: prefs.email === mode }" @click="save({ email: mode })">{{ label }}</button>
        </div>
        <p v-else class="text-sm text-parchment-faint">
          Письма со сводкой новых публикаций приходят, если в <NuxtLink to="/settings" class="link">«Оформить зал»</NuxtLink> указана почта.
        </p>
      </div>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { UserBrief } from '~/utils/types'

definePageMeta({ middleware: 'auth' })
useSeoMeta({ title: 'Уведомления — Allegro', robots: 'noindex, nofollow' })

interface Item { id: number; kind: string; title: string; url: string; created_at: string; read_at?: string | null; actor?: UserBrief | null }
interface Page { items: Item[]; unread: number; next_before: number | null }
interface Prefs { kinds: string[]; push: boolean; email: 'off' | 'daily' | 'weekly'; email_available: boolean; push_key: string }

const KIND_WORDS: Record<string, string> = {
  opus: 'новое сочинение', sketch: 'новый эскиз', article: 'новая статья', performance: 'новое исполнение',
  note: 'новая запись в блоге', news: 'новости сообщества', workshop: 'новая запись',
}
const KIND_LABELS: Record<string, string> = {
  opus: 'Сочинения', sketch: 'Эскизы', article: 'Статьи', performance: 'Исполнения', note: 'Блоги', news: 'Новости',
}
const EMAIL_MODES = { off: 'Не присылать', daily: 'Раз в день', weekly: 'Раз в неделю' } as const

const api = useApi()
const { unread, refresh } = useNotifications()

const { data } = await useAsyncData('notifications', () => api<Page>('/api/notifications'))
const items = ref<Item[]>(data.value?.items || [])
const nextBefore = ref(data.value?.next_before ?? null)
unread.value = data.value?.unread ?? 0
const loading = ref(false)

async function more() {
  loading.value = true
  try {
    const page = await api<Page>('/api/notifications', { params: { before: nextBefore.value } })
    items.value.push(...page.items)
    nextBefore.value = page.next_before
  } finally {
    loading.value = false
  }
}

async function readAll() {
  unread.value = (await api<{ count: number }>('/api/notifications/read', { method: 'POST', body: {} })).count
  const now = new Date().toISOString()
  items.value.forEach((n) => (n.read_at ||= now))
}

function readOne(n: Item) {
  if (n.read_at) return
  n.read_at = new Date().toISOString()
  api<{ count: number }>('/api/notifications/read', { method: 'POST', body: { ids: [n.id] } }).then((r) => (unread.value = r.count)).catch(() => {})
}

const when = (iso: string) => `${formatDate(iso)}, ${formatClock(iso)}`

// ---- settings
const { data: prefsData } = await useAsyncData('notification-settings', () => api<Prefs>('/api/notifications/settings'))
const prefs = ref<Prefs | null>(prefsData.value || null)
const error = ref('')
const busy = ref(false)

async function save(patch: Partial<Prefs>) {
  error.value = ''
  try {
    prefs.value = await api<Prefs>('/api/notifications/settings', { method: 'PUT', body: patch })
    await refresh()
    const page = await api<Page>('/api/notifications')
    items.value = page.items
    nextBefore.value = page.next_before
  } catch (e) {
    error.value = apiError(e)
  }
}

function toggleKind(kind: string) {
  if (!prefs.value) return
  const kinds = prefs.value.kinds.includes(kind) ? prefs.value.kinds.filter((k) => k !== kind) : [...prefs.value.kinds, kind]
  save({ kinds })
}

// ---- push in this browser
const push = usePush()
const pushSupported = ref(false)
const pushOn = ref(false)
const denied = ref(false)
onMounted(async () => {
  pushSupported.value = push.supported.value
  pushOn.value = !!(await push.current())
  denied.value = pushSupported.value && Notification.permission === 'denied'
})

async function turnPushOn() {
  if (!prefs.value) return
  busy.value = true
  error.value = ''
  try {
    pushOn.value = await push.enable(prefs.value.push_key)
    denied.value = !pushOn.value && Notification.permission === 'denied'
    if (pushOn.value && !prefs.value.push) await save({ push: true })
  } catch (e) {
    error.value = apiError(e, 'Не удалось включить уведомления в этом браузере')
  } finally {
    busy.value = false
  }
}

async function turnPushOff() {
  busy.value = true
  try {
    await push.disable()
    pushOn.value = false
  } finally {
    busy.value = false
  }
}
</script>
