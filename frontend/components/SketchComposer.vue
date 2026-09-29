<template>
  <!-- A sketch in a minute: record a voice note here (like in a messenger) or drop a short file, name it, publish -->
  <form class="card space-y-4 !p-5 sm:!p-6" @submit.prevent="publish">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl italic">Новый эскиз</h2>
      <button type="button" class="btn-ghost" aria-label="Закрыть" @click="$emit('close')">✕</button>
    </div>

    <!-- The recording: from the microphone or a file -->
    <div v-if="!audio" class="flex flex-wrap items-center gap-3">
      <button
        v-if="canRecord"
        type="button"
        class="flex items-center gap-2 border px-4 py-2 font-caps text-sm font-semibold tracking-[0.12em] transition"
        :class="recording ? 'border-red-400/70 bg-red-900/20 text-red-200' : 'border-gold/40 text-gold hover:border-gold hover:text-gold-light'"
        @click="recording ? stop() : start()"
      >
        <span class="text-lg leading-none" :class="{ 'animate-pulse': recording }">{{ recording ? '■' : '●' }}</span>
        {{ recording ? `Остановить · ${formatTime(elapsed)}` : 'Записать с микрофона' }}
      </button>
      <label v-if="!recording" class="btn-ghost cursor-pointer">
        <input type="file" accept="audio/*" class="sr-only" @change="pickFile">
        ⎙ Загрузить файл
      </label>
      <span v-if="!recording" class="text-sm text-parchment-faint">до {{ MAX_MINUTES }} минут</span>
    </div>
    <div v-else class="flex items-center gap-3 border border-gold/20 bg-ink-950/50 p-3">
      <audio :src="audio.preview" controls class="min-w-0 flex-1" />
      <button type="button" class="btn-ghost shrink-0 text-sm" @click="reset">Заново</button>
    </div>

    <div>
      <label class="field-label" for="sk-title">Название</label>
      <input id="sk-title" v-model="title" class="field" maxlength="120" placeholder="Импровизация в ре миноре" required>
    </div>
    <textarea v-model="text" rows="2" class="field resize-y" placeholder="Пара слов о наброске (необязательно)" />

    <div class="flex flex-wrap items-center gap-4">
      <label class="flex cursor-pointer items-center gap-2 text-parchment-muted">
        <input v-model="seekingFeedback" type="checkbox" class="accent-[rgb(var(--c-gold))]">
        Ищу отзыв
      </label>
      <button type="submit" class="btn-primary ml-auto" :disabled="busy || recording || !audio || !title.trim()">
        {{ busy ? 'Публикую…' : 'Опубликовать эскиз' }}
      </button>
    </div>
    <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
  </form>
</template>

<script setup lang="ts">
import type { Post, Uploaded } from '~/utils/types'

const emit = defineEmits<{ close: []; published: [post: Post] }>()

const MAX_MINUTES = 10
const api = useApi()
const title = ref('')
const text = ref('')
const seekingFeedback = ref(true)
const busy = ref(false)
const error = ref('')
const audio = ref<{ file: File; preview: string } | null>(null)

// ---- recording from the microphone (MediaRecorder: webm/opus in most browsers, mp4 in Safari)
const canRecord = ref(false)
onMounted(() => (canRecord.value = !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined'))
const recording = ref(false)
const elapsed = ref(0)
let recorder: MediaRecorder | null = null
let chunks: Blob[] = []
let ticker: ReturnType<typeof setInterval> | undefined

async function start() {
  error.value = ''
  let stream: MediaStream
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    error.value = 'Нет доступа к микрофону — разрешите его в браузере или загрузите файл'
    return
  }
  const type = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find((t) => MediaRecorder.isTypeSupported(t)) || ''
  recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined)
  chunks = []
  recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data)
  recorder.onstop = () => {
    stream.getTracks().forEach((t) => t.stop())
    const mime = recorder?.mimeType || type || 'audio/webm'
    const ext = mime.includes('mp4') ? 'm4a' : 'webm'
    const blob = new Blob(chunks, { type: mime.split(';')[0] })
    use(new File([blob], `eskiz.${ext}`, { type: blob.type }))
  }
  recorder.start()
  recording.value = true
  elapsed.value = 0
  ticker = setInterval(() => {
    elapsed.value += 1
    if (elapsed.value >= MAX_MINUTES * 60) stop()
  }, 1000)
}

function stop() {
  clearInterval(ticker)
  recording.value = false
  if (recorder?.state === 'recording') recorder.stop()
}

function pickFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) use(file)
}

function use(file: File) {
  if (audio.value) URL.revokeObjectURL(audio.value.preview)
  audio.value = { file, preview: URL.createObjectURL(file) }
}

function reset() {
  if (audio.value) URL.revokeObjectURL(audio.value.preview)
  audio.value = null
}

onBeforeUnmount(() => {
  stop()
  reset()
})

async function publish() {
  if (!audio.value) return
  busy.value = true
  error.value = ''
  try {
    const data = new FormData()
    data.append('purpose', 'audio')
    data.append('files', audio.value.file)
    const [uploaded] = await api<Uploaded[]>('/api/media', { method: 'POST', body: data })
    const post = await api<Post>('/api/posts', {
      method: 'POST',
      body: {
        kind: 'sketch',
        title: title.value.trim(),
        content_md: text.value.trim(),
        seeking_feedback: seekingFeedback.value,
        attachments: [{ url: uploaded.url, name: uploaded.name, content_type: uploaded.content_type, size: uploaded.size }],
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
