<template>
  <!-- «Предложения»: members suggest features or report problems; everyone sees the answers -->
  <div class="mx-auto max-w-3xl">
    <form v-if="user" class="card mb-10 space-y-4" @submit.prevent="submit">
      <h3 class="text-2xl italic">Предложить или сообщить</h3>
      <div class="flex flex-wrap gap-2">
        <button v-for="(label, k) in FEEDBACK_KINDS" :key="k" type="button" class="chip" :class="{ active: form.kind === k }" @click="form.kind = k as typeof form.kind">{{ label }}</button>
      </div>
      <input v-model="form.title" class="field" required minlength="3" maxlength="200" placeholder="Коротко: что улучшить или что сломалось">
      <textarea v-model="form.body" rows="4" class="field resize-y" required maxlength="5000" placeholder="Подробнее: зачем это нужно, как воспроизвести ошибку…" />
      <div class="flex items-center gap-3">
        <button type="submit" class="btn-primary ml-auto" :disabled="busy">Отправить</button>
      </div>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </form>
    <p v-else class="mb-10 text-center font-elegant text-lg italic text-parchment-muted">
      Предложения пишут участники сообщества. <NuxtLink :to="`/login?next=${encodeURIComponent(route.fullPath)}`" class="link">Войти</NuxtLink>
    </p>

    <div class="mb-6 flex flex-wrap gap-2">
      <button type="button" class="chip" :class="{ active: !status }" @click="status = null">Все</button>
      <button v-for="(label, s) in FEEDBACK_STATUSES" :key="s" type="button" class="chip" :class="{ active: status === s }" @click="status = s">{{ label }}</button>
    </div>

    <EmptyState v-if="!items.length">{{ status ? 'Здесь пока ничего' : 'Предложений пока нет — ваше будет первым' }}</EmptyState>
    <div class="space-y-5">
      <article v-for="f in items" :key="f.id" class="card !p-5">
        <header class="flex flex-wrap items-center gap-3">
          <span class="chip" :class="{ active: f.status === 'planned' || f.status === 'done' }">{{ FEEDBACK_STATUSES[f.status] }}</span>
          <span class="text-sm text-parchment-faint">{{ FEEDBACK_KINDS[f.kind] }} · {{ f.author.display_name }} · {{ formatDate(f.created_at) }}</span>
          <button
            v-if="isAdmin || (user?.id === f.author.id && f.status === 'new' && !f.reply_md)"
            type="button"
            class="ml-auto text-sm text-parchment-faint transition hover:text-red-300"
            @click="remove(f)"
          >
            Удалить
          </button>
        </header>
        <h3 class="mt-3 text-xl">{{ f.title }}</h3>
        <p class="mt-2 whitespace-pre-line text-parchment-muted">{{ f.body }}</p>

        <div v-if="f.reply_md" class="mt-4 border-l-2 border-gold/50 pl-4">
          <p class="eyebrow text-xs">Ответ</p>
          <MarkdownContent :text="f.reply_md" variant="compact" class="mt-1" />
        </div>

        <!-- Administrators answer and set the status -->
        <form v-if="isAdmin" class="mt-4 space-y-3 border-t border-gold/10 pt-4" @submit.prevent="answer(f)">
          <div class="flex flex-wrap gap-2">
            <button v-for="(label, s) in FEEDBACK_STATUSES" :key="s" type="button" class="chip" :class="{ active: (drafts[f.id]?.status ?? f.status) === s }" @click="draftOf(f).status = s">{{ label }}</button>
          </div>
          <textarea v-model="draftOf(f).reply_md" rows="2" class="field resize-y" placeholder="Ответ (Markdown)" />
          <button type="submit" class="btn-secondary px-4 py-1.5 text-sm">Сохранить ответ</button>
        </form>
      </article>
    </div>
    <div v-if="items.length < total" class="mt-8 text-center">
      <button class="btn-secondary" @click="more">Ещё</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Feedback, Page } from '~/utils/types'

const api = useApi()
const route = useRoute()
const { user, isAdmin } = useAuth()

const status = ref<string | null>(null)
const limit = ref(30)
const { data, refresh } = await useAsyncData(
  'feedback',
  () => api<Page<Feedback>>('/api/feedback', { params: { limit: limit.value, ...(status.value ? { status: status.value } : {}) } }),
  { watch: [status, limit] },
)
const items = computed(() => data.value?.items || [])
const total = computed(() => data.value?.total || 0)
const more = () => (limit.value += 30)

const form = reactive({ kind: 'idea' as Feedback['kind'], title: '', body: '' })
const busy = ref(false)
const error = ref('')

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await api('/api/feedback', { method: 'POST', body: form })
    form.title = form.body = ''
    await refresh()
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}

const drafts = reactive<Record<string, { status: Feedback['status']; reply_md: string }>>({})
const draftOf = (f: Feedback) => (drafts[f.id] ||= { status: f.status, reply_md: f.reply_md || '' })

async function answer(f: Feedback) {
  const d = draftOf(f)
  await api(`/api/feedback/${f.id}`, { method: 'PATCH', body: { status: d.status, reply_md: d.reply_md } })
  delete drafts[f.id]
  await refresh()
}

async function remove(f: Feedback) {
  if (!confirm('Удалить предложение?')) return
  await api(`/api/feedback/${f.id}`, { method: 'DELETE' })
  await refresh()
}
</script>
