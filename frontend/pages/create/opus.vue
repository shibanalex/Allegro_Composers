<template>
  <div class="mx-auto max-w-4xl">
    <PageHeader eyebrow="Мастерская автора" :title="editing ? 'Редактирование опуса' : 'Новый опус'" />

    <!-- New works are published by composers (the role is chosen in «Оформить зал») -->
    <div v-if="!editing && !can('publish_opus')" class="card text-center font-elegant text-xl italic text-parchment-muted">
      Публиковать сочинения могут композиторы. Роль меняется в <NuxtLink to="/settings" class="link">«Оформить зал»</NuxtLink>.
    </div>

    <form v-else class="space-y-12" @submit.prevent="save">
      <!-- 1. Passport -->
      <fieldset class="space-y-5">
        <legend class="section-title">I. Паспорт сочинения</legend>
        <div>
          <label class="field-label" for="o-title">Название</label>
          <input id="o-title" v-model="form.title" class="field text-xl" required placeholder="Фортепианное трио ре минор">
        </div>
        <div>
          <label class="field-label" for="o-sub">Подзаголовок</label>
          <input id="o-sub" v-model="form.subtitle" class="field" placeholder="op. 1, Ч. I: Allegro">
        </div>
        <div>
          <p class="field-label">Жанр и состав</p>
          <div class="flex flex-wrap gap-2">
            <button v-for="(g, id) in GENRES" :key="id" type="button" class="chip" :class="{ active: form.genre === id }" :aria-pressed="form.genre === id" @click="chooseGenre(String(id))">
              {{ g.label }}
            </button>
          </div>
        </div>
        <div>
          <p class="field-label">Инструменты <span class="normal-case tracking-normal text-parchment-faint">— подставлены по жанру, можно изменить</span></p>
          <InstrumentPicker v-model="instruments" @update:model-value="instrumentsEdited = true" />
        </div>
        <div class="grid gap-5 sm:grid-cols-2">
          <div>
            <label class="field-label" for="o-key">Тональность <span class="normal-case tracking-normal text-parchment-faint">— необязательно</span></label>
            <input id="o-key" v-model="form.key_signature" class="field" placeholder="ре минор" list="keys">
            <datalist id="keys"><option v-for="k in KEY_SUGGESTIONS" :key="k" :value="k" /></datalist>
          </div>
          <div>
            <label class="field-label" for="o-year">Год</label>
            <input id="o-year" v-model.number="form.year" type="number" min="1000" max="2100" class="field">
          </div>
        </div>
        <div>
          <p class="field-label">Обложка</p>
          <div v-if="form.cover_url" class="frame frame-thin relative w-72">
            <div class="frame-inner aspect-square"><img :src="form.cover_url" class="h-full w-full object-cover" alt=""></div>
            <button type="button" class="btn-ghost absolute right-1 top-1 z-10 bg-ink-950/70 px-2 text-sm" @click="form.cover_url = null">✕</button>
          </div>
          <FileDropzone v-else label="Загрузить обложку" hint="обрежется до квадрата" accept="image/*" purpose="cover" @uploaded="(f) => (form.cover_url = f[0].url)" @error="fail" />
        </div>
      </fieldset>

      <!-- 2. Recording -->
      <fieldset class="space-y-5">
        <legend class="section-title">II. Запись</legend>
        <div class="flex flex-wrap gap-2">
          <button v-for="(label, v) in AUDIO_TYPES" :key="v" type="button" class="chip" :class="{ active: form.audio_type === v }" @click="form.audio_type = v">{{ label }}</button>
        </div>
        <div v-if="form.audio_type === 'hosted_file'">
          <div v-if="form.audio_source" class="flex items-center gap-3 border border-gold/20 bg-ink-950/50 p-3">
            <span class="chip">{{ audioName || 'аудиофайл' }}</span>
            <button type="button" class="btn-ghost ml-auto text-sm" @click="form.audio_source = null">Заменить</button>
          </div>
          <FileDropzone v-else label="Загрузить запись" hint="MP3, WAV, FLAC, OGG" accept="audio/*" purpose="audio" @uploaded="onAudio" @error="fail" />
        </div>
        <div v-else-if="form.audio_type === 'youtube'">
          <label class="field-label" for="o-yt">Ссылка на YouTube</label>
          <input id="o-yt" v-model="form.audio_source" class="field" placeholder="https://youtu.be/…">
          <div class="mt-3 grid grid-cols-2 gap-5 sm:w-1/2">
            <div>
              <label class="field-label" for="o-dur">Длительность (мм:сс)</label>
              <input id="o-dur" v-model="durationText" class="field font-mono" placeholder="08:30">
            </div>
          </div>
        </div>
      </fieldset>

      <!-- 3. Scores + sync -->
      <fieldset class="space-y-5">
        <legend class="section-title">III. Ноты и синхронизация</legend>
        <p class="font-elegant text-lg italic text-parchment-muted">
          Загрузите один формат или оба сразу. MusicXML даёт бегунок по нотам, PDF — печатную партитуру, которая листается вместе с записью.
          На странице опуса слушатель переключается между ними.
        </p>

        <HintBubble id="opus-files" side="top" text="Достаточно чего-то одного: записи, PDF или MusicXML. MusicXML из нотного редактора даёт живые ноты — бегунок идёт за записью, клик по ноте перематывает.">
          <span class="block" />
        </HintBubble>
        <div class="grid gap-5 md:grid-cols-2">
          <!-- MusicXML -->
          <div class="card space-y-3">
            <p class="font-display text-xl italic text-parchment">♫ MusicXML</p>
            <p class="text-sm text-parchment-faint">
              Экспорт из MuseScore, Sibelius, Dorico, Finale: <span class="font-mono">.musicxml</span>, <span class="font-mono">.xml</span>, <span class="font-mono">.mxl</span>.
              Золотой бегунок идёт по нотам, клик по ноте перематывает запись.
            </p>
            <div v-if="form.musicxml_file_key" class="flex flex-wrap items-center gap-3 border border-gold/20 bg-ink-950/50 p-3">
              <span class="chip">♫ {{ musicxmlName || 'MusicXML' }}</span>
              <button type="button" class="btn-ghost ml-auto text-sm" @click="form.musicxml_file_key = null">Заменить</button>
            </div>
            <FileDropzone v-else label="Загрузить MusicXML" hint=".musicxml, .xml, .mxl" accept=".musicxml,.xml,.mxl" purpose="musicxml" @uploaded="onMusicXml" @error="fail" />
          </div>

          <!-- PDF -->
          <div class="card space-y-3">
            <p class="font-display text-xl italic text-parchment">𝄞 PDF</p>
            <p class="text-sm text-parchment-faint">Печатная партитура. Читатель листает страницы сам, как книгу.</p>
            <div v-if="form.score_file_key" class="flex flex-wrap items-center gap-3 border border-gold/20 bg-ink-950/50 p-3">
              <span class="chip">𝄞 PDF · {{ form.score_page_count }} стр.</span>
              <button type="button" class="btn-ghost ml-auto text-sm" @click="form.score_file_key = null; form.score_page_count = null">Заменить</button>
            </div>
            <FileDropzone v-else label="Загрузить PDF" hint=".pdf" accept="application/pdf" purpose="score" @uploaded="onScore" @error="fail" />
          </div>
        </div>

        <div>
          <p class="field-label">Кто может скачать ноты (PDF и MusicXML)</p>
          <div class="flex flex-wrap gap-2">
            <button v-for="(label, v) in SCORE_ACCESS" :key="v" type="button" class="chip" :class="{ active: form.score_access === v }" @click="form.score_access = v">{{ label }}</button>
          </div>
        </div>

        <!-- Sync with the recording -->
        <div v-if="form.audio_type !== 'none' && form.musicxml_file_key" class="card space-y-6">
          <div>
            <p class="font-display text-xl italic text-parchment">Синхронизация с записью</p>
            <p class="mt-1 text-sm text-parchment-faint">Прослушайте запись здесь и ставьте отметки кнопкой ⏱ в нужный момент.</p>
          </div>
          <audio v-if="form.audio_type === 'hosted_file' && previewUrl" ref="preview" :src="previewUrl" controls class="w-full" @loadedmetadata="onPreviewMeta" />

          <!-- MusicXML: offset + optional measure markers -->
          <template v-if="form.musicxml_file_key">
            <div class="sm:w-1/2">
              <label class="field-label" for="o-offset">Первая доля звучит на (мм:сс)</label>
              <div class="flex gap-2">
                <input id="o-offset" v-model="offsetText" class="field font-mono" placeholder="00:00">
                <button v-if="preview" type="button" class="btn-ghost shrink-0 px-2 text-sm" title="Отметить текущий момент записи" @click="offsetText = formatTime(preview.currentTime)">⏱</button>
              </div>
              <p class="mt-1 text-xs text-parchment-faint">Если в записи есть тишина или вступление перед нотами.</p>
            </div>
            <div>
              <p class="field-label">Отметки тактов — для живого исполнения с агогикой (необязательно)</p>
              <p class="mb-3 text-sm text-parchment-faint">Без отметок бегунок идёт по темпу, записанному в файле. С отметками — подстраивается под исполнение между ними.</p>
              <div v-for="(m, i) in measureRows" :key="i" class="mb-2 flex items-center gap-2">
                <span class="w-12 font-caps text-sm font-semibold tracking-[0.1em] text-parchment-muted">такт</span>
                <input v-model.number="m.measure" type="number" min="1" class="field w-24 py-1.5" placeholder="№">
                <input v-model="m.time" class="field w-32 py-1.5 font-mono" placeholder="мм:сс">
                <button v-if="preview" type="button" class="btn-ghost px-2 text-sm" title="Отметить текущий момент записи" @click="m.time = formatTime(preview.currentTime)">⏱</button>
                <button type="button" class="btn-ghost px-2 text-sm" aria-label="Убрать" @click="measureRows.splice(i, 1)">✕</button>
              </div>
              <button type="button" class="link font-caps text-sm font-semibold tracking-[0.15em]" @click="addMeasureRow">+ Отметить такт</button>
            </div>
          </template>

        </div>
      </fieldset>

      <!-- 4. Explication -->
      <fieldset class="space-y-3">
        <legend class="section-title">IV. Экспликация · анализ</legend>
        <p class="text-sm text-parchment-faint">Markdown. Таймкоды вида 00:24 станут ссылками на момент записи.</p>
        <textarea v-model="form.description_md" rows="10" class="field resize-y" placeholder="Экспозиция строится на терцовых соотношениях…" />
      </fieldset>

      <div class="flex flex-wrap items-center gap-4 border-t border-gold/15 pt-6">
        <HintBubble id="opus-status" side="top" text="Черновик видите только вы. «★ На выставке» — сочинение встанет на витрину вашего зала; убрать и вернуть можно в любой момент.">
          <select v-model="form.status" class="field w-auto">
            <option v-for="(label, v) in STATUSES" :key="v" :value="v">{{ label }}</option>
          </select>
        </HintBubble>
        <label class="flex cursor-pointer items-center gap-2 text-parchment-muted">
          <input v-model="form.featured" type="checkbox" class="accent-[rgb(var(--c-gold))]">
          ★ На выставке
        </label>
        <button type="submit" class="btn-primary" :disabled="busy">{{ editing ? 'Сохранить' : 'Опубликовать' }}</button>
        <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import type { Opus, Uploaded } from '~/utils/types'

definePageMeta({ middleware: 'auth' })

const { can } = useAuth()

const AUDIO_TYPES = { hosted_file: 'Аудиофайл', youtube: 'YouTube', none: 'Без записи' } as const
const KEY_SUGGESTIONS = ['до мажор', 'до минор', 'ре мажор', 'ре минор', 'ми мажор', 'ми минор', 'фа мажор', 'фа минор', 'соль мажор', 'соль минор', 'ля мажор', 'ля минор', 'си мажор', 'си минор', 'ми-бемоль мажор', 'си-бемоль мажор', 'атональная']

const route = useRoute()
const api = useApi()
const editing = typeof route.query.edit === 'string' ? route.query.edit : null
useSeoMeta({ title: editing ? 'Редактирование опуса — Allegro' : 'Новый опус — Allegro', robots: 'noindex, nofollow' })

const form = reactive({
  title: '', subtitle: '', genre: 'solo', key_signature: '',
  year: new Date().getFullYear() as number | null,
  description_md: '', cover_url: null as string | null,
  audio_type: 'hosted_file' as Opus['audio_type'], audio_source: null as string | null, audio_duration_seconds: null as number | null,
  score_file_key: null as string | null, score_page_count: null as number | null,
  score_access: 'free' as Opus['score_access'], status: 'published' as Opus['status'],
  musicxml_file_key: null as string | null, audio_offset_seconds: 0, featured: false,
})
const musicxmlName = ref('')
const measureRows = ref<{ measure: number | null; time: string }[]>([])
const offsetText = computed({
  get: () => (form.audio_offset_seconds ? formatTime(form.audio_offset_seconds) : ''),
  set: (v: string) => (form.audio_offset_seconds = parseTime(v) ?? 0),
})
const addMeasureRow = () => {
  const last = measureRows.value.at(-1)?.measure
  measureRows.value.push({ measure: last ? last + 8 : 1, time: preview.value ? formatTime(preview.value.currentTime) : '' })
}
const onMusicXml = (files: Uploaded[]) => {
  form.musicxml_file_key = files[0].key
  musicxmlName.value = files[0].name
}
// The genre suggests the instruments until the composer edits the list themselves
const instruments = ref<string[]>([...GENRES.solo.instruments])
const instrumentsEdited = ref(false)
function chooseGenre(genre: string) {
  form.genre = genre
  if (!instrumentsEdited.value || !instruments.value.length) {
    instruments.value = [...(GENRES[genre]?.instruments || [])]
    instrumentsEdited.value = false
  }
}
const audioName = ref('')
const previewUrl = ref<string | null>(null)
const preview = ref<HTMLAudioElement>()
const busy = ref(false)
const error = ref('')
const fail = (m: string) => (error.value = m)

const durationText = computed({
  get: () => (form.audio_duration_seconds ? formatTime(form.audio_duration_seconds) : ''),
  set: (v: string) => (form.audio_duration_seconds = parseTime(v)),
})

/** What the form would send: on editing, only what differs from this is sent (an untouched field never changes) */
function payload() {
  return {
    ...form,
    subtitle: form.subtitle || null,
    key_signature: form.key_signature || null,
    description_md: form.description_md || null,
    audio_source: form.audio_type === 'none' ? null : form.audio_source,
    instruments: instruments.value,
    measure_markers: form.audio_type === 'none' || !form.musicxml_file_key
      ? []
      : measureRows.value
          .filter((m) => m.measure && m.time && parseTime(m.time) != null)
          .map((m) => ({ measure_number: Number(m.measure), timestamp_seconds: parseTime(m.time)! })),
  }
}
let original: Record<string, unknown> = {}

if (editing) {
  const opus = await api<Opus>(`/api/opuses/${editing}`)
  Object.assign(form, {
    ...Object.fromEntries(Object.keys(form).map((k) => [k, (opus as any)[k] ?? (form as any)[k]])),
    subtitle: opus.subtitle || '', key_signature: opus.key_signature || '',
    description_md: opus.description_md || '',
    audio_source: opus.audio_type === 'youtube' ? `https://youtu.be/${opus.audio_source}` : opus.audio_source,
    // Storage keys of the files, as the API gives them (a missing key would mean «remove the file»)
    score_file_key: opus.score_file_key ?? null,
    musicxml_file_key: opus.musicxml_file_key ?? null,
  })
  instruments.value = [...opus.instruments]
  instrumentsEdited.value = true
  measureRows.value = opus.measure_markers.map((m) => ({ measure: m.measure_number, time: formatTime(m.timestamp_seconds) }))
  musicxmlName.value = opus.musicxml_url?.split('/').pop()?.replace(/^[0-9a-f]{12}_/, '') || ''
  previewUrl.value = opus.audio_url || null
  audioName.value = opus.audio_source?.split('/').pop()?.replace(/^[0-9a-f]{12}_/, '') || ''
  original = JSON.parse(JSON.stringify(payload()))
}

function onAudio(files: Uploaded[], raw: File[]) {
  form.audio_source = files[0].key
  audioName.value = files[0].name
  previewUrl.value = files[0].url
  // Read the duration locally
  const probe = new Audio(URL.createObjectURL(raw[0]))
  probe.addEventListener('loadedmetadata', () => (form.audio_duration_seconds = Math.round(probe.duration * 100) / 100))
}

async function onScore(files: Uploaded[], raw: File[]) {
  form.score_file_key = files[0].key
  try {
    const pdfjs = await import('pdfjs-dist')
    const worker = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
    pdfjs.GlobalWorkerOptions.workerSrc = worker.default
    const doc = await pdfjs.getDocument({ data: await raw[0].arrayBuffer() }).promise
    form.score_page_count = doc.numPages
    doc.destroy()
  } catch {
    form.score_page_count = Number(prompt('Сколько страниц в партитуре?', '1')) || 1
  }
}

const onPreviewMeta = () => {
  if (preview.value && isFinite(preview.value.duration)) form.audio_duration_seconds = Math.round(preview.value.duration * 100) / 100
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    const body = payload()
    let opus: Opus
    if (editing) {
      // Only what was changed goes to the server
      const changed = Object.fromEntries(Object.entries(body).filter(([k, v]) => JSON.stringify(v) !== JSON.stringify(original[k])))
      opus = Object.keys(changed).length
        ? await api<Opus>(`/api/opuses/${editing}`, { method: 'PATCH', body: changed })
        : await api<Opus>(`/api/opuses/${editing}`)
    } else {
      opus = await api<Opus>('/api/opuses', { method: 'POST', body })
    }
    await navigateTo(`/opus/${opus.slug}`)
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.section-title {
  @apply mb-4 w-full border-b border-gold/15 pb-3 font-display text-3xl italic text-parchment;
}
</style>
