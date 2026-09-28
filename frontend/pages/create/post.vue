<template>
  <div class="mx-auto max-w-4xl">
    <PageHeader eyebrow="Публикация" :title="editing ? 'Редактирование' : TITLES[form.kind]" />

    <form class="space-y-8" @submit.prevent="save">
      <div class="flex flex-wrap gap-2">
        <!-- Only the kinds the member's role allows (a blog post is for everyone) -->
        <button v-for="k in kinds" :key="k" type="button" class="chip" :class="{ active: form.kind === k }" @click="form.kind = k">{{ POST_KINDS[k] }}</button>
      </div>

      <div>
        <!-- A blog post may be untitled, like a channel message -->
        <label class="field-label" for="p-title">Заголовок{{ form.kind === 'note' ? ' (необязательно)' : '' }}</label>
        <input id="p-title" v-model="form.title" class="field text-xl" :required="form.kind !== 'note'" :placeholder="PLACEHOLDERS[form.kind]">
      </div>
      <div>
        <label class="field-label" for="p-excerpt">Кратко</label>
        <input id="p-excerpt" v-model="form.excerpt" class="field" maxlength="512">
      </div>

      <!-- A review: an article about a work on the site -->
      <div v-if="form.kind === 'article' || form.kind === 'workshop'">
        <label class="field-label" for="p-opus">Об опусе — если это обзор (необязательно)</label>
        <select id="p-opus" v-model="form.opus_id" class="field">
          <option :value="null">— без опуса —</option>
          <option v-for="o in allOpuses" :key="o.id" :value="o.id">{{ o.title }} · {{ o.author.display_name }}</option>
        </select>
        <p class="mt-1 text-sm text-parchment-faint">Таймкоды вида 02:15 в тексте и комментариях будут перематывать запись этого опуса.</p>
      </div>

      <div>
        <div class="mb-1.5 flex items-center justify-between">
          <label class="field-label mb-0" for="p-content">Текст (Markdown)</label>
          <button type="button" class="font-caps text-sm font-semibold tracking-[0.18em] text-gold" @click="previewing = !previewing">
            {{ previewing ? 'Редактировать' : 'Предпросмотр' }}
          </button>
        </div>
        <div v-if="previewing" class="min-h-[18rem] border border-ink-600 bg-ink-950/60 p-6">
          <MarkdownContent :text="form.content_md" :timecodes="!!form.opus_id" />
        </div>
        <textarea v-else id="p-content" ref="contentEl" v-model="form.content_md" rows="16" class="field resize-y leading-relaxed" :required="!form.attachments.length"
          placeholder="## Раздел&#10;&#10;Текст… **жирный**, *курсив*, > цитата, - список" />
      </div>

      <div>
        <p class="field-label">Обложка</p>
        <div v-if="form.cover_url" class="frame frame-thin relative w-72">
          <div class="frame-inner aspect-[16/10]"><img :src="form.cover_url" class="h-full w-full object-cover" alt=""></div>
          <button type="button" class="btn-ghost absolute right-1 top-1 z-10 bg-ink-950/70 px-2 text-sm" @click="form.cover_url = null">✕</button>
        </div>
        <FileDropzone v-else label="Загрузить обложку" accept="image/*" purpose="image" @uploaded="(f) => (form.cover_url = f[0].url)" @error="fail" />
      </div>

      <div>
        <p class="field-label">Эскизы, партитуры, MIDI, демо</p>
        <FileDropzone multiple label="Добавить материалы" @uploaded="onFiles" @error="fail" />
        <AttachmentList v-if="form.attachments.length" :files="form.attachments" class="mt-4">
          <template #action="{ file }">
            <button v-if="isImage(file)" type="button" class="btn-ghost text-sm" @click="insertImage(file)">В текст</button>
            <button type="button" class="btn-ghost text-sm hover:text-red-300" @click="form.attachments = form.attachments.filter((a) => a.url !== file.url)">✕</button>
          </template>
        </AttachmentList>
      </div>

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
import type { Attachment, Opus, Page, Post, Uploaded } from '~/utils/types'

definePageMeta({ middleware: 'auth' })

const TITLES = { article: 'Новая статья', note: 'Запись в блог', news: 'Новость', workshop: 'Мастерская' } as const
const PLACEHOLDERS = {
  article: 'Терцовые соотношения в романтической экспозиции',
  note: 'Ноктюрн, который не хотел заканчиваться',
  news: 'В Allegro появились исполнения',
  workshop: 'Послушайте экспозицию моего трио — не проседает ли фактура?',
} as const

const route = useRoute()
const api = useApi()
const editing = typeof route.query.edit === 'string' ? route.query.edit : null
const { can } = useAuth()
// A blog post is for everyone; articles need a composer's or theorist's role; news — an administrator
const kinds = computed(() => {
  const list: Post['kind'][] = ['note']
  if (can('publish_article')) list.push('article')
  if (can('publish_news')) list.push('news')
  if (form.kind === 'workshop') list.push('workshop') // an old thread being edited
  return list
})
const requested = route.query.kind as Post['kind'] | undefined
const initialKind: Post['kind'] = requested && (requested === 'note' || (requested === 'article' && can('publish_article')) || (requested === 'news' && can('publish_news')))
  ? requested
  : can('publish_article') ? 'article' : 'note'

const form = reactive({
  kind: initialKind as Post['kind'],
  title: '', excerpt: '', content_md: '', cover_url: null as string | null,
  attachments: [] as Attachment[], opus_id: null as string | null, status: 'published',
})
const previewing = ref(false)
const busy = ref(false)
const error = ref('')
const contentEl = ref<HTMLTextAreaElement>()
const fail = (m: string) => (error.value = m)

useSeoMeta({ title: () => `${editing ? 'Редактирование' : TITLES[form.kind]} — Allegro`, robots: 'noindex, nofollow' })

// Works on the site an article can review
const { data: published } = await useAsyncData('review-opuses', () => api<Page<Opus>>('/api/opuses', { params: { limit: 100, sort: 'title' } }))
const allOpuses = computed(() => published.value?.items || [])

if (editing) {
  const post = await api<Post>(`/api/posts/${editing}`)
  Object.assign(form, {
    kind: post.kind, title: post.title, excerpt: post.excerpt || '', content_md: post.content_md, cover_url: post.cover_url,
    attachments: post.attachments, opus_id: post.opus?.id || null, status: post.status,
  })
} else if (typeof route.query.opus === 'string') {
  form.opus_id = route.query.opus
}

const onFiles = (files: Uploaded[]) =>
  form.attachments.push(...files.map(({ url, name, content_type, size }) => ({ url, name, content_type, size })))

async function insertImage(file: Attachment) {
  previewing.value = false
  await nextTick()
  const pos = contentEl.value?.selectionStart ?? form.content_md.length
  form.content_md = `${form.content_md.slice(0, pos)}\n![${file.name}](${file.url})\n${form.content_md.slice(pos)}`
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    const body = { ...form, excerpt: form.excerpt || null, opus_id: form.kind === 'article' || form.kind === 'workshop' ? form.opus_id : null }
    const post = editing
      ? await api<Post>(`/api/posts/${editing}`, { method: 'PATCH', body })
      : await api<Post>('/api/posts', { method: 'POST', body })
    await navigateTo(`/posts/${post.slug}`)
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
