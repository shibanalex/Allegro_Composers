<template>
  <!-- «Блог»: like a Telegram channel — short posts with photos, audio and files, newest first -->
  <div class="mx-auto max-w-2xl">
    <!-- Composer (owner only) -->
    <form v-if="isOwner" class="card mb-12 space-y-4" @submit.prevent="publish">
      <textarea
        v-model="text"
        rows="3"
        class="field resize-y font-serif text-lg leading-relaxed"
        placeholder="Написать в блог… Markdown работает: **жирный**, *курсив*, > цитата"
        @keydown.ctrl.enter.prevent="publish"
        @keydown.meta.enter.prevent="publish"
      />
      <div v-if="pending.length" class="flex flex-wrap gap-2">
        <span v-for="(a, i) in pending" :key="a.url" class="chip gap-2">
          {{ isImage(a) ? '◫' : isAudio(a) ? '♪' : '⎙' }} {{ a.name }}
          <button type="button" class="text-parchment-faint hover:text-red-300" aria-label="Убрать" @click="pending.splice(i, 1)">✕</button>
        </span>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <label class="btn-ghost cursor-pointer px-2" title="Прикрепить фото, аудио или файл">
          <input type="file" multiple class="sr-only" @change="attach">
          <span class="text-lg">⎙</span> {{ uploading ? 'Загрузка…' : 'Вложение' }}
        </label>
        <NuxtLink to="/create/post?kind=article" class="btn-ghost px-2 text-sm">¶ Длинная статья</NuxtLink>
        <button type="submit" class="btn-primary ml-auto px-5 py-1.5 text-sm" :disabled="busy || uploading || (!text.trim() && !pending.length)">Опубликовать</button>
      </div>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </form>

    <EmptyState v-if="!posts.length">{{ isOwner ? 'Первая запись в блоге — за вами' : 'В блоге пока тихо' }}</EmptyState>

    <template v-for="(p, i) in posts" :key="p.id">
      <!-- Day separator, as in a messenger -->
      <div v-if="i === 0 || dayOf(p) !== dayOf(posts[i - 1])" class="my-8 flex items-center gap-4">
        <span class="rule flex-1" />
        <span class="font-caps text-sm font-semibold tracking-[0.2em] text-gold/70">{{ dayOf(p) }}</span>
        <span class="rule flex-1" />
      </div>

      <article class="card mb-5 !p-5 sm:!p-6">
        <!-- A long article: shown as a card leading to the full text -->
        <NuxtLink v-if="p.kind === 'article'" :to="`/posts/${p.slug}`" class="group flex gap-5">
          <div v-if="p.cover_url" class="frame frame-thin hidden h-24 w-32 shrink-0 sm:block">
            <div class="frame-inner"><img :src="p.cover_url" alt="" class="h-full w-full object-cover"></div>
          </div>
          <div class="min-w-0">
            <p class="eyebrow text-xs">Статья</p>
            <h3 class="mt-1 text-2xl italic transition group-hover:text-gold-light">{{ p.title }}</h3>
            <p class="mt-2 line-clamp-2 font-elegant text-lg italic text-parchment-muted">{{ p.excerpt || stripMarkdown(p.content_md, 180) }}</p>
            <span class="mt-2 inline-block font-caps text-sm font-semibold tracking-[0.15em] text-gold">Читать →</span>
          </div>
        </NuxtLink>

        <!-- Editing a channel post in place -->
        <form v-else-if="editing?.id === p.id" class="space-y-4" @submit.prevent="saveEdit(p)">
          <textarea
            v-model="editing.text"
            rows="6"
            class="field resize-y font-serif text-lg leading-relaxed"
            @keydown.ctrl.enter.prevent="saveEdit(p)"
            @keydown.meta.enter.prevent="saveEdit(p)"
            @keydown.esc="editing = null"
          />
          <div v-if="editing.attachments.length" class="flex flex-wrap gap-2">
            <span v-for="(a, j) in editing.attachments" :key="a.url" class="chip gap-2">
              {{ isImage(a) ? '◫' : isAudio(a) ? '♪' : '⎙' }} {{ a.name }}
              <button type="button" class="text-parchment-faint hover:text-red-300" aria-label="Убрать" @click="editing.attachments.splice(j, 1)">✕</button>
            </span>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <label class="btn-ghost cursor-pointer px-2" title="Прикрепить фото, аудио или файл">
              <input type="file" multiple class="sr-only" @change="(e) => attach(e, editing!.attachments)">
              <span class="text-lg">⎙</span> {{ uploading ? 'Загрузка…' : 'Вложение' }}
            </label>
            <NuxtLink :to="`/create/post?edit=${p.slug}`" class="btn-ghost px-2 text-sm" title="Заголовок, обложка, черновик">Полный редактор</NuxtLink>
            <button type="button" class="btn-ghost ml-auto px-3 text-sm" @click="editing = null">Отмена</button>
            <button type="submit" class="btn-primary px-5 py-1.5 text-sm" :disabled="busy || uploading || (!editing.text.trim() && !editing.attachments.length)">Сохранить</button>
          </div>
          <p v-if="editError" class="text-sm text-red-300">{{ editError }}</p>
        </form>

        <!-- A channel post -->
        <template v-else>
          <h3 v-if="p.title" class="mb-2 text-2xl italic">{{ p.title }}</h3>
          <MarkdownContent v-if="p.content_md" :text="p.content_md" variant="compact" />
          <ImageGallery v-if="images(p).length" :images="images(p)" class="mt-4" />
          <div v-for="a in audios(p)" :key="a.url" class="mt-4 border border-gold/20 bg-ink-950/50 p-3">
            <p class="mb-2 truncate text-sm text-parchment-muted">♪ {{ a.name }}</p>
            <audio :src="a.url" controls preload="none" class="w-full" />
          </div>
          <AttachmentList v-if="files(p).length" :files="files(p)" class="mt-4" />
        </template>

        <footer class="mt-4 flex items-center gap-5 text-sm text-parchment-faint">
          <span>{{ timeOf(p) }}</span>
          <span title="Просмотры">👁 {{ p.view_count }}</span>
          <NuxtLink :to="`/posts/${p.slug}`" class="transition hover:text-gold-light">{{ discussLabel(p) }}</NuxtLink>
          <template v-if="isOwner && editing?.id !== p.id">
            <NuxtLink v-if="p.kind === 'article'" :to="`/create/post?edit=${p.slug}`" class="ml-auto transition hover:text-gold-light">Изменить</NuxtLink>
            <button v-else type="button" class="ml-auto transition hover:text-gold-light" @click="startEdit(p)">Изменить</button>
            <button type="button" class="transition hover:text-red-300" @click="remove(p)">Удалить</button>
          </template>
        </footer>
      </article>
    </template>

    <div v-if="posts.length < total" class="mt-8 text-center">
      <button class="btn-secondary" :disabled="loading" @click="more">Ранее</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Attachment, Page, Post, Uploaded } from '~/utils/types'

const props = defineProps<{ username: string; isOwner: boolean; initial: Page<Post> }>()

const api = useApi()
const { user, registrationOpen } = useAuth()
const posts = ref<Post[]>([...props.initial.items])
const total = ref(props.initial.total)
const loading = ref(false)

const isAudio = (a: Attachment) => a.content_type?.startsWith('audio/')
const images = (p: Post) => p.attachments.filter(isImage)
const audios = (p: Post) => p.attachments.filter(isAudio)
const files = (p: Post) => p.attachments.filter((a) => !isImage(a) && !isAudio(a))

const dayOf = (p: Post) => formatDate(p.created_at)
const timeOf = (p: Post) => formatClock(p.created_at)

/** Members are invited to discuss; while sign-ups are closed a visitor is simply offered the post page */
function discussLabel(p: Post) {
  if (p.comment_count) return `✎ ${p.comment_count} ${plural(p.comment_count, 'комментарий', 'комментария', 'комментариев')}`
  return user.value || registrationOpen.value ? '✎ Обсудить' : 'Открыть →'
}

async function more() {
  loading.value = true
  try {
    const page = await api<Page<Post>>('/api/posts', {
      params: { author: props.username, kind: ['note', 'article'], limit: 20, offset: posts.value.length, ...(props.isOwner ? { mine: true } : {}) },
    })
    posts.value.push(...page.items)
    total.value = page.total
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------- composer

const text = ref('')
const pending = ref<Attachment[]>([])
const uploading = ref(false)
const busy = ref(false)
const error = ref('')

/** Upload each file with the purpose its type calls for (images, audio, anything else) */
async function attach(e: Event, into = pending.value) {
  const input = e.target as HTMLInputElement
  const list = Array.from(input.files || [])
  input.value = ''
  uploading.value = true
  error.value = ''
  try {
    for (const file of list) {
      const purpose = file.type.startsWith('image/') ? 'image' : file.type.startsWith('audio/') ? 'audio' : 'attachment'
      const form = new FormData()
      form.append('purpose', purpose)
      form.append('files', file)
      const [saved] = await api<Uploaded[]>('/api/media', { method: 'POST', body: form })
      into.push({ url: saved.url, name: saved.name, content_type: saved.content_type, size: saved.size })
    }
  } catch (err) {
    const message = apiError(err, 'Не удалось загрузить файл')
    if (into === pending.value) error.value = message
    else editError.value = message
  } finally {
    uploading.value = false
  }
}

async function publish() {
  if (busy.value || (!text.value.trim() && !pending.value.length)) return
  busy.value = true
  error.value = ''
  try {
    const post = await api<Post>('/api/posts', {
      method: 'POST',
      body: { kind: 'note', content_md: text.value.trim(), attachments: pending.value },
    })
    posts.value.unshift(post)
    total.value += 1
    text.value = ''
    pending.value = []
  } catch (err) {
    error.value = apiError(err)
  } finally {
    busy.value = false
  }
}

// ---------------------------------------------------------------- editing a post in place

const editing = ref<{ id: string; text: string; attachments: Attachment[] } | null>(null)
const editError = ref('')

function startEdit(p: Post) {
  editing.value = { id: p.id, text: p.content_md, attachments: [...p.attachments] }
  editError.value = ''
}

async function saveEdit(p: Post) {
  const draft = editing.value
  if (!draft || busy.value || (!draft.text.trim() && !draft.attachments.length)) return
  busy.value = true
  editError.value = ''
  try {
    const saved = await api<Post>(`/api/posts/${p.slug}`, {
      method: 'PATCH',
      body: { content_md: draft.text.trim(), attachments: draft.attachments },
    })
    posts.value = posts.value.map((x) => (x.id === saved.id ? saved : x))
    editing.value = null
  } catch (err) {
    editError.value = apiError(err)
  } finally {
    busy.value = false
  }
}

async function remove(p: Post) {
  if (!confirm('Удалить запись?')) return
  await api(`/api/posts/${p.slug}`, { method: 'DELETE' })
  posts.value = posts.value.filter((x) => x.id !== p.id)
  total.value -= 1
}
</script>
