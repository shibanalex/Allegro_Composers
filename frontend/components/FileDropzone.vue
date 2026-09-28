<template>
  <label
    class="flex cursor-pointer flex-col items-center justify-center gap-1 border border-dashed px-6 py-6 text-center transition"
    :class="dragging ? 'border-gold bg-gold/5' : 'border-ink-600 hover:border-gold/60'"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
  >
    <input type="file" class="sr-only" :multiple="multiple" :accept="accept" @change="onPick">
    <span class="font-display text-3xl text-gold/60">{{ uploading ? '…' : '+' }}</span>
    <span class="font-elegant text-lg text-parchment-muted">{{ uploading ? 'Загрузка…' : label }}</span>
    <span class="text-sm text-parchment-faint">{{ hint || 'перетащите файл или нажмите для выбора' }}</span>
  </label>
</template>

<script setup lang="ts">
import type { Uploaded } from '~/utils/types'

const props = withDefaults(defineProps<{
  label?: string
  hint?: string
  accept?: string
  multiple?: boolean
  purpose?: 'score' | 'musicxml' | 'audio' | 'image' | 'cover' | 'attachment'
}>(), { label: 'Добавить файлы', multiple: false, purpose: 'attachment' })
const emit = defineEmits<{ uploaded: [files: Uploaded[], raw: File[]]; error: [message: string] }>()

const api = useApi()
const dragging = ref(false)
const uploading = ref(false)

async function upload(list: FileList | null | undefined) {
  const files = Array.from(list || []).slice(0, props.multiple ? undefined : 1)
  if (!files.length) return
  const form = new FormData()
  form.append('purpose', props.purpose)
  files.forEach((f) => form.append('files', f))
  uploading.value = true
  try {
    emit('uploaded', await api<Uploaded[]>('/api/media', { method: 'POST', body: form }), files)
  } catch (e) {
    emit('error', apiError(e, 'Не удалось загрузить файл'))
  } finally {
    uploading.value = false
  }
}

const onDrop = (e: DragEvent) => {
  dragging.value = false
  upload(e.dataTransfer?.files)
}
const onPick = (e: Event) => {
  const input = e.target as HTMLInputElement
  upload(input.files)
  input.value = ''
}
</script>
