<template>
  <section>
    <h2 class="flex items-baseline gap-3 font-caps text-lg font-semibold tracking-[0.2em] text-gold">
      {{ title }} <span class="font-display text-base font-normal italic tracking-normal text-parchment-faint">({{ comments.length }})</span>
    </h2>

    <!-- New critique -->
    <form v-if="user" id="comment-form" class="mt-5 space-y-3" @submit.prevent="submit(null)">
      <!-- the stretch selected on the waveform: the comment will be about it -->
      <p v-if="selection" class="flex flex-wrap items-center gap-2 text-sm text-parchment-muted">
        Комментарий к отрезку
        <button type="button" class="timecode" title="Прослушать отрезок" @click="$emit('seek', selection.start, selection.end)">{{ formatStretch(selection.start, selection.end) }}</button>
        <button type="button" class="text-parchment-faint transition hover:text-red-300" aria-label="Не привязывать к отрезку" @click="selection = null">✕</button>
      </p>
      <textarea
        ref="field"
        v-model="draft"
        rows="3"
        class="field resize-y font-serif"
        :placeholder="opus ? 'Ваш комментарий… Таймкоды вида 02:15 станут ссылками на запись' : 'Ваш комментарий…'"
      />
      <div class="flex flex-wrap items-center gap-3">
        <label v-if="opus && opus.audio_type !== 'none' && !selection" class="flex cursor-pointer items-center gap-2 text-sm text-parchment-muted">
          <input v-model="attachTime" type="checkbox" class="accent-[rgb(var(--c-gold))]">
          Привязать к моменту
          <span class="font-mono text-gold-light">{{ formatTime(player.isCurrent(opus.slug) ? player.time : 0) }}</span>
        </label>
        <button type="submit" class="btn-primary ml-auto px-5 py-1.5 text-sm" :disabled="sending || !draft.trim()">Отправить</button>
      </div>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </form>
    <p v-else class="mt-4 font-elegant text-lg italic text-parchment-muted">
      <NuxtLink :to="`/login?next=${encodeURIComponent(route.fullPath)}`" class="link">Войдите</NuxtLink>
      или <NuxtLink :to="`/register?next=${encodeURIComponent(route.fullPath)}`" class="link">откройте свой зал</NuxtLink>, чтобы оставить комментарий.
    </p>

    <ul v-if="roots.length" class="mt-8 space-y-7">
      <CommentItem
        v-for="c in roots"
        :key="c.id"
        :comment="c"
        :children="children"
        :can-moderate="canModerate"
        :depth="0"
        @seek="(t, end) => $emit('seek', t, end)"
        @reply="reply"
        @remove="remove"
      />
    </ul>
    <p v-else-if="loading" class="mt-8 font-elegant text-lg italic text-parchment-faint">Загружаю комментарии…</p>
    <p v-else class="mt-8 font-elegant text-lg italic text-parchment-faint">Пока тихо. Будьте первым, кто выскажется.</p>
  </section>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { Comment, Opus, OpusBrief } from '~/utils/types'

const props = defineProps<{
  target: { opus_id?: string; post_id?: string }
  /** The recording that timecodes refer to */
  opus?: Opus | OpusBrief | null
  /** Author of the opus/post - may delete any comment */
  ownerId: string
  title?: string
}>()
defineEmits<{ seek: [seconds: number, end?: number] }>()

const api = useApi()
const route = useRoute()
const player = usePlayer()
const { user, can } = useAuth()

// Comments load alongside the page and never hold it up: it shows first, the discussion fills in
const { data, pending: loading } = useLazyAsyncData(`comments-${props.target.opus_id || props.target.post_id}`, () =>
  api<Comment[]>('/api/comments', { params: props.target }),
)
const comments = ref<Comment[]>(data.value || [])
watch(data, (value) => (comments.value = value || []))

const roots = computed(() => comments.value.filter((c) => !c.parent_id))
const children = computed(() => {
  const map: Record<string, Comment[]> = {}
  for (const c of comments.value) if (c.parent_id) (map[c.parent_id] ||= []).push(c)
  return map
})
// The commenter, the owner of the work or post, and moderators may remove a comment
const canModerate = (c: Comment) => !!user.value && (user.value.id === c.author.id || user.value.id === props.ownerId || can('moderate'))

const draft = ref('')
const attachTime = ref(false)
const field = ref<HTMLTextAreaElement>()

// On an opus page: the stretch selected on the waveform, and the commented stretches lit on it
const stretches = props.target.opus_id ? useStretches(props.target.opus_id) : null
const selection = computed({
  get: () => stretches?.selection.value ?? null,
  set: (value) => { if (stretches) stretches.selection.value = value },
})
watch(comments, (list) => {
  if (!stretches) return
  stretches.commented.value = list
    .filter((c) => c.timestamp_marker != null && c.timestamp_end != null)
    .map((c) => ({ id: c.id, start: c.timestamp_marker!, end: c.timestamp_end! }))
}, { deep: true, immediate: true })
// «Комментировать отрезок» in the transport brings the reader here
watch(selection, (value, old) => {
  if (value && !old) nextTick(() => field.value?.focus({ preventScroll: true }))
})
const sending = ref(false)
const error = ref('')

async function submit(parentId: string | null, text = draft.value) {
  if (!text.trim()) return
  sending.value = true
  error.value = ''
  try {
    const stretch = !parentId ? selection.value : null
    const timestamp = stretch ? stretch.start
      : !parentId && attachTime.value && props.opus && player.isCurrent(props.opus.slug) ? player.time : null
    const created = await api<Comment>('/api/comments', {
      method: 'POST',
      body: { ...props.target, parent_id: parentId, content_md: text.trim(), timestamp_marker: timestamp, timestamp_end: stretch?.end ?? null },
    })
    comments.value.push(created)
    if (!parentId) {
      draft.value = ''
      attachTime.value = false
      selection.value = null
    }
    return true
  } catch (e) {
    error.value = apiError(e)
    return false
  } finally {
    sending.value = false
  }
}

const reply = async (parentId: string, text: string, done: () => void) => {
  if (await submit(parentId, text)) done()
}

async function remove(c: Comment) {
  if (!confirm('Удалить комментарий вместе с ответами?')) return
  await api(`/api/comments/${c.id}`, { method: 'DELETE' })
  // Drop the comment and its whole subtree
  const gone = new Set([c.id])
  let grew = true
  while (grew) {
    grew = false
    for (const x of comments.value) if (x.parent_id && gone.has(x.parent_id) && !gone.has(x.id)) gone.add(x.id), (grew = true)
  }
  comments.value = comments.value.filter((x) => !gone.has(x.id))
}
</script>
