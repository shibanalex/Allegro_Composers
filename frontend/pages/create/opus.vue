<template>
  <div class="mx-auto max-w-4xl">
    <PageHeader eyebrow="Мастерская автора" :title="editing ? 'Редактирование опуса' : 'Новый опус'" />

    <form class="space-y-12" @submit.prevent="save">
      <!-- 1. Passport -->
      <fieldset class="space-y-5">
        <legend class="section-title">I. Паспорт сочинения</legend>
        <div>
          <label class="field-label" for="o-title">Название</label>
          <input id="o-title" v-model="form.title" class="field text-xl" required placeholder="Фортепианное трио ре минор">
        </div>
        <div class="grid gap-5 sm:grid-cols-2">
          <div>
            <label class="field-label" for="o-sub">Подзаголовок</label>
            <input id="o-sub" v-model="form.subtitle" class="field" placeholder="op. 1, Ч. I: Allegro">
          </div>
          <div>
            <label class="field-label" for="o-instr">Инструментовка</label>
            <input id="o-instr" v-model="form.instrumentation" class="field" placeholder="Ф-но, Скрипка, Вч.">
          </div>
          <div>
            <label class="field-label" for="o-ens">Состав</label>
            <select id="o-ens" v-model="form.ensemble" class="field">
              <option v-for="(label, v) in ENSEMBLES" :key="v" :value="v">{{ label }}</option>
            </select>
          </div>
          <div>
            <label class="field-label" for="o-form">Форма</label>
            <select id="o-form" v-model="form.form" class="field">
              <option v-for="(label, v) in FORMS" :key="v" :value="v">{{ label }}</option>
            </select>
          </div>
          <div>
            <label class="field-label" for="o-key">Тональность</label>
            <input id="o-key" v-model="form.key_signature" class="field" placeholder="ре минор" list="keys">
            <datalist id="keys"><option v-for="k in KEY_SUGGESTIONS" :key="k" :value="k" /></datalist>
          </div>
          <div class="grid grid-cols-2 gap-5">
            <div>
              <label class="field-label" for="o-diff">Сложность</label>
              <select id="o-diff" v-model.number="form.difficulty" class="field">
                <option :value="null">—</option>
                <option v-for="(label, v) in DIFFICULTY" :key="v" :value="Number(v)">{{ v }} · {{ label }}</option>
              </select>
            </div>
            <div>
              <label class="field-label" for="o-year">Год</label>
              <input id="o-year" v-model.number="form.year" type="number" min="1000" max="2100" class="field">
            </div>
          </div>
        </div>
        <div>
          <label class="field-label" for="o-tags">Инструменты и теги (через запятую)</label>
          <input id="o-tags" v-model="tagsText" class="field" placeholder="фортепиано, скрипка, виолончель">
        </div>
        <div>
          <p class="field-label">Обложка</p>
          <div v-if="form.cover_url" class="frame frame-thin relative w-72">
            <div class="frame-inner aspect-[16/10]"><img :src="form.cover_url" class="h-full w-full object-cover" alt=""></div>
            <button type="button" class="btn-ghost absolute right-1 top-1 z-10 bg-ink-950/70 px-2 text-sm" @click="form.cover_url = null">✕</button>
          </div>
          <FileDropzone v-else label="Загрузить обложку" accept="image/*" purpose="image" @uploaded="(f) => (form.cover_url = f[0].url)" @error="fail" />
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
            <p class="text-sm text-parchment-faint">Печатная партитура. Страницы перелистываются, как в книге, в такт записи.</p>
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
        <div v-if="form.audio_type !== 'none' && (form.musicxml_file_key || form.score_page_count)" class="card space-y-6">
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

          <!-- PDF: page turns -->
          <div v-if="form.score_page_count">
            <p class="field-label">Перелистывание страниц PDF</p>
            <div class="mb-3 flex flex-wrap gap-2">
              <button type="button" class="chip" :class="{ active: pageMode === 'auto' }" :disabled="!form.musicxml_file_key" @click="pageMode = 'auto'">
                Автоматически по MusicXML
              </button>
              <button type="button" class="chip" :class="{ active: pageMode === 'manual' }" @click="pageMode = 'manual'">Вручную</button>
            </div>
            <p v-if="pageMode === 'auto'" class="text-sm text-parchment-faint">
              Страницы перелистнутся там, где в MusicXML стоят разрывы страниц (их записывает нотный редактор), с учётом темпа и отметок тактов.
              Число страниц в PDF и MusicXML должно совпадать — иначе задайте отметки вручную.
            </p>
            <template v-else>
              <div class="mb-3 flex flex-wrap items-center gap-3">
                <p class="text-sm text-parchment-faint">С какой секунды записи начинается каждая страница.</p>
                <button type="button" class="link ml-auto font-caps text-sm font-semibold tracking-[0.15em]" :disabled="!duration" @click="distribute">Разложить равномерно</button>
              </div>
              <div class="grid gap-2 sm:grid-cols-2">
                <div v-for="p in form.score_page_count" :key="p" class="flex items-center gap-3">
                  <span class="w-16 font-caps text-sm font-semibold tracking-[0.1em] text-parchment-muted">стр. {{ p }}</span>
                  <input v-model="markerText[p]" class="field py-1.5 font-mono" :placeholder="p === 1 ? '00:00' : 'мм:сс'">
                  <button v-if="preview" type="button" class="btn-ghost shrink-0 px-2 text-sm" title="Отметить текущий момент записи" @click="stamp(p)">⏱</button>
                </div>
              </div>
            </template>
          </div>
        </div>
      </fieldset>

      <!-- 4. Explication -->
      <fieldset class="space-y-3">
        <legend class="section-title">IV. Экспликация · анализ</legend>
        <p class="text-sm text-parchment-faint">Markdown. Таймкоды вида 00:24 станут ссылками на момент записи.</p>
        <textarea v-model="form.description_md" rows="10" class="field resize-y" placeholder="Экспозиция строится на терцовых соотношениях…" />
      </fieldset>

      <div class="flex flex-wrap items-center gap-4 border-t border-gold/15 pt-6">
        <select v-model="form.status" class="field w-auto">
          <option v-for="(label, v) in STATUSES" :key="v" :value="v">{{ label }}</option>
        </select>
        <button type="submit" class="btn-primary" :disabled="busy">{{ editing ? 'Сохранить' : 'Опубликовать' }}</button>
        <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import type { Opus, Uploaded } from '~/utils/types'

definePageMeta({ middleware: 'auth' })

const AUDIO_TYPES = { hosted_file: 'Аудиофайл', youtube: 'YouTube', none: 'Без записи' } as const
const KEY_SUGGESTIONS = ['до мажор', 'до минор', 'ре мажор', 'ре минор', 'ми мажор', 'ми минор', 'фа мажор', 'фа минор', 'соль мажор', 'соль минор', 'ля мажор', 'ля минор', 'си мажор', 'си минор', 'ми-бемоль мажор', 'си-бемоль мажор', 'атональная']

const route = useRoute()
const api = useApi()
const editing = typeof route.query.edit === 'string' ? route.query.edit : null
useSeoMeta({ title: editing ? 'Редактирование опуса — Allegro' : 'Новый опус — Allegro' })

const form = reactive({
  title: '', subtitle: '', instrumentation: '', ensemble: 'solo', form: 'miniature', key_signature: '',
  difficulty: null as number | null, year: new Date().getFullYear() as number | null,
  description_md: '', cover_url: null as string | null,
  audio_type: 'hosted_file' as Opus['audio_type'], audio_source: null as string | null, audio_duration_seconds: null as number | null,
  score_file_key: null as string | null, score_page_count: null as number | null,
  score_access: 'free' as Opus['score_access'], status: 'published' as Opus['status'],
  musicxml_file_key: null as string | null, audio_offset_seconds: 0,
})
const musicxmlName = ref('')
// PDF page turns: derived from the MusicXML page breaks, or set by hand
const pageMode = ref<'auto' | 'manual'>('manual')
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
  if (!Object.entries(markerText).some(([p, t]) => Number(p) > 1 && t)) pageMode.value = 'auto'
}
watch(() => form.musicxml_file_key, (key) => {
  if (!key) pageMode.value = 'manual'
})
const tagsText = ref('')
const markerText = reactive<Record<number, string>>({})
const audioName = ref('')
const previewUrl = ref<string | null>(null)
const preview = ref<HTMLAudioElement>()
const busy = ref(false)
const error = ref('')
const fail = (m: string) => (error.value = m)

const duration = computed(() => form.audio_duration_seconds || 0)
const durationText = computed({
  get: () => (form.audio_duration_seconds ? formatTime(form.audio_duration_seconds) : ''),
  set: (v: string) => (form.audio_duration_seconds = parseTime(v)),
})

const keyFromUrl = (url?: string | null) => (url?.startsWith('/media/') ? url.slice('/media/'.length) : null)

if (editing) {
  const opus = await api<Opus>(`/api/opuses/${editing}`)
  Object.assign(form, {
    ...Object.fromEntries(Object.keys(form).map((k) => [k, (opus as any)[k] ?? (form as any)[k]])),
    subtitle: opus.subtitle || '', instrumentation: opus.instrumentation || '', key_signature: opus.key_signature || '',
    description_md: opus.description_md || '',
    audio_source: opus.audio_type === 'youtube' ? `https://youtu.be/${opus.audio_source}` : opus.audio_source,
    // The API returns public URLs; the form sends storage keys back (a null key would delete the file)
    score_file_key: keyFromUrl(opus.score_url),
    musicxml_file_key: keyFromUrl(opus.musicxml_url),
  })
  tagsText.value = opus.tags.join(', ')
  pageMode.value = opus.auto_page_markers && opus.musicxml_url ? 'auto' : 'manual'
  measureRows.value = opus.measure_markers.map((m) => ({ measure: m.measure_number, time: formatTime(m.timestamp_seconds) }))
  musicxmlName.value = opus.musicxml_url?.split('/').pop()?.replace(/^[0-9a-f]{12}_/, '') || ''
  opus.markers.forEach((m) => (markerText[m.page_number] = formatTime(m.timestamp_seconds)))
  previewUrl.value = opus.audio_url || null
  audioName.value = opus.audio_source?.split('/').pop()?.replace(/^[0-9a-f]{12}_/, '') || ''
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
  if (!markerText[1]) markerText[1] = '00:00'
}

const onPreviewMeta = () => {
  if (preview.value && isFinite(preview.value.duration)) form.audio_duration_seconds = Math.round(preview.value.duration * 100) / 100
}
const stamp = (page: number) => {
  if (preview.value) markerText[page] = formatTime(preview.value.currentTime)
}
const distribute = () => {
  const pages = form.score_page_count || 1
  for (let p = 1; p <= pages; p++) markerText[p] = formatTime(((p - 1) * duration.value) / pages)
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    // [] tells the API to derive page turns from the MusicXML page breaks
    const markers = form.audio_type === 'none' || !form.score_page_count || pageMode.value === 'auto'
      ? []
      : Object.entries(markerText)
          .filter(([p, t]) => t && Number(p) <= form.score_page_count!)
          .map(([p, t]) => ({ page_number: Number(p), timestamp_seconds: parseTime(t) }))
          .filter((m) => m.timestamp_seconds != null)
    const body = {
      ...form,
      subtitle: form.subtitle || null,
      instrumentation: form.instrumentation || null,
      key_signature: form.key_signature || null,
      description_md: form.description_md || null,
      audio_source: form.audio_type === 'none' ? null : form.audio_source,
      tags: tagsText.value.split(',').map((t) => t.trim()).filter(Boolean),
      markers,
      measure_markers: form.audio_type === 'none' || !form.musicxml_file_key
        ? []
        : measureRows.value
            .filter((m) => m.measure && m.time && parseTime(m.time) != null)
            .map((m) => ({ measure_number: Number(m.measure), timestamp_seconds: parseTime(m.time)! })),
    }
    const opus = editing
      ? await api<Opus>(`/api/opuses/${editing}`, { method: 'PATCH', body })
      : await api<Opus>('/api/opuses', { method: 'POST', body })
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
