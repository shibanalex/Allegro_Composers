<template>
  <!-- Add or edit a performance: a piece from the site or any other, and its recording -->
  <form class="card space-y-5" @submit.prevent="save">
    <h3 class="text-2xl italic">{{ editing ? 'Изменить исполнение' : 'Новое исполнение' }}</h3>

    <div>
      <label class="field-label" for="pf-opus">Сочинение с сайта</label>
      <select id="pf-opus" v-model="form.opus_id" class="field">
        <option :value="null">— другое сочинение —</option>
        <option v-for="o in opuses" :key="o.id" :value="o.id">{{ o.title }} · {{ o.author.display_name }}</option>
      </select>
    </div>
    <!-- A work from the site keeps its composer's title; another piece is described here -->
    <div v-if="!form.opus_id" class="grid gap-5 sm:grid-cols-2">
      <div>
        <label class="field-label" for="pf-title">Что исполняется</label>
        <input id="pf-title" v-model="form.title" class="field" required maxlength="255" placeholder="Баллада №1 соль минор">
      </div>
      <div>
        <label class="field-label" for="pf-composer">Композитор</label>
        <input id="pf-composer" v-model="form.composer_name" class="field" maxlength="160" placeholder="Фредерик Шопен">
      </div>
    </div>

    <div>
      <p class="field-label">Запись</p>
      <div class="mb-3 flex gap-2">
        <button type="button" class="chip" :class="{ active: form.audio_type === 'youtube' }" @click="form.audio_type = 'youtube'">YouTube</button>
        <button type="button" class="chip" :class="{ active: form.audio_type === 'hosted_file' }" @click="form.audio_type = 'hosted_file'">Аудиофайл</button>
      </div>
      <input v-if="form.audio_type === 'youtube'" v-model="youtube" class="field" placeholder="https://youtu.be/…" :required="form.audio_type === 'youtube'">
      <template v-else>
        <p v-if="fileName" class="mb-2 text-parchment-muted">♪ {{ fileName }}</p>
        <FileDropzone label="Загрузить запись" hint="MP3, WAV, OGG, FLAC, M4A" accept="audio/*" purpose="audio" @uploaded="onAudio" @error="(m) => (error = m)" />
      </template>
    </div>

    <div class="grid gap-5 sm:grid-cols-2">
      <div>
        <label class="field-label" for="pf-year">Год записи</label>
        <input id="pf-year" v-model.number="form.recorded_year" type="number" min="1900" max="2100" class="field">
      </div>
      <div>
        <label class="field-label" for="pf-status">Видимость</label>
        <select id="pf-status" v-model="form.status" class="field">
          <option v-for="(label, v) in STATUSES" :key="v" :value="v">{{ label }}</option>
        </select>
      </div>
    </div>
    <div>
      <label class="field-label" for="pf-about">Об исполнении</label>
      <textarea id="pf-about" v-model="form.description_md" rows="3" class="field resize-y" maxlength="20000" placeholder="Инструмент, зал, мысли о трактовке…" />
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <button type="button" class="btn-ghost" @click="$emit('cancel')">Отмена</button>
      <button type="submit" class="btn-primary ml-auto" :disabled="busy">{{ editing ? 'Сохранить' : 'Опубликовать' }}</button>
    </div>
    <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
  </form>
</template>

<script setup lang="ts">
import type { Opus, Page, Performance, Uploaded } from '~/utils/types'

const props = defineProps<{ editing?: Performance | null; opusId?: string | null }>()
const emit = defineEmits<{ saved: [p: Performance]; cancel: [] }>()

const api = useApi()
const e = props.editing
const form = reactive({
  title: e?.title || '',
  composer_name: e?.composer_name || '',
  opus_id: e?.opus?.id || props.opusId || null as string | null,
  audio_type: (e?.audio_type || 'youtube') as Performance['audio_type'],
  audio_source: e?.audio_type === 'hosted_file' ? e.audio_source || '' : '',
  recorded_year: e?.recorded_year || null as number | null,
  status: e?.status || 'published',
  description_md: e?.description_md || '',
})
const youtube = ref(e?.audio_type === 'youtube' ? `https://youtu.be/${e.audio_source}` : '')
const fileName = ref(e?.audio_type === 'hosted_file' ? (e.audio_source || '').split('/').pop()?.replace(/^[0-9a-f]{12}_/, '') : '')
const busy = ref(false)
const error = ref('')

// Works on the site a performance can point to
const { data: page } = await useAsyncData('performance-opuses', () => api<Page<Opus>>('/api/opuses', { params: { limit: 100, sort: 'title' } }))
const opuses = computed(() => page.value?.items || [])

function onAudio(files: Uploaded[]) {
  form.audio_source = files[0].key
  fileName.value = files[0].name
}

async function save() {
  error.value = ''
  const audio_source = form.audio_type === 'youtube' ? youtube.value.trim() : form.audio_source
  if (!audio_source) {
    error.value = form.audio_type === 'youtube' ? 'Вставьте ссылку на видео' : 'Загрузите запись'
    return
  }
  busy.value = true
  try {
    const body = {
      ...form,
      audio_source,
      title: form.opus_id ? null : form.title.trim(),
      composer_name: form.opus_id ? null : form.composer_name.trim() || null,
      description_md: form.description_md.trim() || null,
      recorded_year: form.recorded_year || null,
    }
    const saved = props.editing
      ? await api<Performance>(`/api/performances/${props.editing.id}`, { method: 'PATCH', body })
      : await api<Performance>('/api/performances', { method: 'POST', body })
    emit('saved', saved)
  } catch (err) {
    error.value = apiError(err)
  } finally {
    busy.value = false
  }
}
</script>
