<template>
  <!-- «Процитировать» a post or «Поделиться» a work: a blog post of one's own with the thing inside -->
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/80 p-4 backdrop-blur-sm" @click.self="$emit('close')">
      <form class="card w-full max-w-xl space-y-4 !p-6" role="dialog" aria-modal="true" :aria-label="heading" @submit.prevent="send">
        <div class="flex items-center justify-between">
          <h2 class="text-2xl italic">{{ heading }}</h2>
          <button type="button" class="btn-ghost" aria-label="Закрыть" @click="$emit('close')">✕</button>
        </div>
        <textarea ref="field" v-model="text" rows="4" class="field" :placeholder="quote ? 'Ваши слова к цитате (необязательно)' : 'Что вы хотите сказать об этом сочинении?'" />
        <QuoteCard v-if="quote" :post="quote" />
        <OpusMiniCard v-else-if="opus" :opus="opus" />
        <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
        <div class="flex items-center justify-end gap-3">
          <button type="button" class="btn-ghost" @click="$emit('close')">Отмена</button>
          <button type="submit" class="btn-primary" :disabled="busy">{{ busy ? 'Публикую…' : 'Опубликовать в блоге' }}</button>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import type { OpusBrief, Post, PostBrief } from '~/utils/types'

const props = defineProps<{ quote?: PostBrief | null; opus?: OpusBrief | null }>()
const emit = defineEmits<{ close: []; published: [post: Post] }>()

const api = useApi()
const text = ref('')
const busy = ref(false)
const error = ref('')
const field = ref<HTMLTextAreaElement>()
const heading = computed(() => (props.quote ? 'Процитировать запись' : 'Поделиться сочинением'))
onMounted(() => field.value?.focus())

async function send() {
  busy.value = true
  error.value = ''
  try {
    const post = await api<Post>('/api/posts', {
      method: 'POST',
      body: {
        kind: 'note',
        // a quotation may go without words of one's own; the post then consists of the quoted one
        content_md: text.value.trim(),
        quote_post_id: props.quote?.id ?? null,
        opus_id: props.opus?.id ?? null,
      },
    })
    emit('published', post)
    emit('close')
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
