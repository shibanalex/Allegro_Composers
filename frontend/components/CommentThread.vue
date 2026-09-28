<template>
  <section v-if="canJoin || comments.length">
    <h2 class="flex items-baseline gap-3 font-caps text-lg font-semibold tracking-[0.2em] text-gold">
      {{ title }} <span class="font-display text-base font-normal italic tracking-normal text-parchment-faint">({{ comments.length }})</span>
    </h2>

    <!-- New critique -->
    <form v-if="user" class="mt-5 space-y-3" @submit.prevent="submit(null)">
      <textarea
        v-model="draft"
        rows="3"
        class="field resize-y font-serif"
        :placeholder="opus ? 'Ваш разбор… Таймкоды вида 02:15 станут ссылками на запись' : 'Ваш комментарий…'"
      />
      <div class="flex flex-wrap items-center gap-3">
        <label v-if="opus && opus.audio_type !== 'none'" class="flex cursor-pointer items-center gap-2 text-sm text-parchment-muted">
          <input v-model="attachTime" type="checkbox" class="accent-[rgb(var(--c-gold))]">
          Привязать к моменту
          <span class="font-mono text-gold-light">{{ formatTime(player.isCurrent(opus.slug) ? player.time : 0) }}</span>
        </label>
        <button type="submit" class="btn-primary ml-auto px-5 py-1.5 text-sm" :disabled="sending || !draft.trim()">Отправить</button>
      </div>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </form>
    <p v-else-if="canJoin" class="mt-4 font-elegant text-lg italic text-parchment-muted">
      <NuxtLink :to="`/login?next=${encodeURIComponent(route.fullPath)}`" class="link">Войдите</NuxtLink>, чтобы оставить {{ opus ? 'рецензию' : 'комментарий' }}.
    </p>

    <ul v-if="roots.length" class="mt-8 space-y-7">
      <CommentItem
        v-for="c in roots"
        :key="c.id"
        :comment="c"
        :children="children"
        :can-moderate="canModerate"
        :depth="0"
        @seek="(t) => $emit('seek', t)"
        @reply="reply"
        @remove="remove"
      />
    </ul>
    <p v-else-if="canJoin" class="mt-8 font-elegant text-lg italic text-parchment-faint">Пока тихо. Будьте первым, кто выскажется.</p>
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
defineEmits<{ seek: [seconds: number] }>()

const api = useApi()
const route = useRoute()
const player = usePlayer()
const { user, registrationOpen, can } = useAuth()
// A visitor can take part only by logging in or signing up; while sign-ups are closed they just read
const canJoin = computed(() => !!user.value || registrationOpen.value)

const { data } = await useAsyncData(`comments-${props.target.opus_id || props.target.post_id}`, () =>
  api<Comment[]>('/api/comments', { params: props.target }),
)
const comments = ref<Comment[]>(data.value || [])

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
const sending = ref(false)
const error = ref('')

async function submit(parentId: string | null, text = draft.value) {
  if (!text.trim()) return
  sending.value = true
  error.value = ''
  try {
    const timestamp = !parentId && attachTime.value && props.opus && player.isCurrent(props.opus.slug) ? player.time : null
    const created = await api<Comment>('/api/comments', {
      method: 'POST',
      body: { ...props.target, parent_id: parentId, content_md: text.trim(), timestamp_marker: timestamp },
    })
    comments.value.push(created)
    if (!parentId) {
      draft.value = ''
      attachTime.value = false
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
