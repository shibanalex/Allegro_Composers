<template>
  <li>
    <div class="flex gap-3">
      <NuxtLink :to="`/@${comment.author.username}`" class="shrink-0"><UserAvatar :user="comment.author" :size="36" /></NuxtLink>
      <div class="min-w-0 flex-1">
        <p class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <NuxtLink :to="`/@${comment.author.username}`" class="font-display italic text-gold-light transition hover:text-gold">
            {{ comment.author.pseudonym || comment.author.display_name }}
          </NuxtLink>
          <button v-if="comment.timestamp_marker != null" type="button" class="timecode" @click="$emit('seek', comment.timestamp_marker)">
            {{ formatTime(comment.timestamp_marker) }}
          </button>
          <span class="text-xs text-parchment-faint">{{ formatDate(comment.created_at) }}</span>
        </p>
        <MarkdownContent :text="comment.content_md" timecodes variant="compact" class="mt-1.5" @seek="(t) => $emit('seek', t)" />

        <div class="mt-2 flex gap-4 font-caps text-sm font-semibold tracking-[0.12em] text-parchment-faint">
          <button v-if="user && depth < 3" type="button" class="transition hover:text-gold" @click="replying = !replying">Ответить</button>
          <button v-if="canModerate(comment)" type="button" class="transition hover:text-red-300" @click="$emit('remove', comment)">Удалить</button>
        </div>

        <form v-if="replying" class="mt-3 flex gap-2" @submit.prevent="sendReply">
          <textarea v-model="text" rows="2" class="field resize-y text-base" placeholder="Ваш ответ…" />
          <button type="submit" class="btn-secondary self-end px-4 py-1.5 text-sm" :disabled="!text.trim()">↵</button>
        </form>

        <ul v-if="children[comment.id]?.length" class="mt-5 space-y-5 border-l border-gold/20 pl-4 sm:pl-6">
          <CommentItem
            v-for="c in children[comment.id]"
            :key="c.id"
            :comment="c"
            :children="children"
            :can-moderate="canModerate"
            :depth="depth + 1"
            @seek="(t) => $emit('seek', t)"
            @reply="(...args) => $emit('reply', ...args)"
            @remove="(x) => $emit('remove', x)"
          />
        </ul>
      </div>
    </div>
  </li>
</template>

<script setup lang="ts">
import type { Comment } from '~/utils/types'

const props = defineProps<{
  comment: Comment
  children: Record<string, Comment[]>
  canModerate: (c: Comment) => boolean
  depth: number
}>()
const emit = defineEmits<{
  seek: [seconds: number]
  reply: [parentId: string, text: string, done: () => void]
  remove: [comment: Comment]
}>()

const { user } = useAuth()
const replying = ref(false)
const text = ref('')

const sendReply = () =>
  emit('reply', props.comment.id, text.value, () => {
    text.value = ''
    replying.value = false
  })
</script>
