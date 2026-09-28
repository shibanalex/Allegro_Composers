<template>
  <!-- «Материалы»: books, links and files the composer shares -->
  <div>
    <div v-if="isOwner" class="mb-10">
      <div v-if="!adding" class="flex justify-end">
        <button type="button" class="btn-secondary px-4 py-1.5 text-sm" @click="adding = true">+ Материал</button>
      </div>

      <form v-else class="card space-y-5" @submit.prevent="save">
        <div class="flex flex-wrap gap-2">
          <button v-for="(label, k) in KIND_ONE" :key="k" type="button" class="chip" :class="{ active: form.kind === k }" @click="form.kind = k">{{ label }}</button>
        </div>
        <div class="grid gap-5 sm:grid-cols-2">
          <div>
            <label class="field-label" for="m-title">Название</label>
            <input id="m-title" v-model="form.title" class="field" required maxlength="255" :placeholder="PLACEHOLDERS[form.kind]">
          </div>
          <div v-if="form.kind !== 'file'">
            <label class="field-label" for="m-url">{{ form.kind === 'link' ? 'Адрес' : 'Ссылка (магазин, библиотека) — необязательно' }}</label>
            <input id="m-url" v-model="form.url" class="field" :required="form.kind === 'link'" placeholder="https://…">
          </div>
        </div>
        <div>
          <label class="field-label" for="m-desc">Описание</label>
          <textarea id="m-desc" v-model="form.description" rows="3" class="field resize-y" placeholder="Чем полезно, кому пригодится" />
        </div>
        <div v-if="form.kind !== 'link'" class="grid gap-5" :class="form.kind === 'book' ? 'sm:grid-cols-2' : ''">
          <div>
            <p class="field-label">{{ form.kind === 'book' ? 'Файл книги (необязательно)' : 'Файл' }}</p>
            <span v-if="form.file" class="chip gap-2">⎙ {{ form.file.name }} <button type="button" class="hover:text-red-300" @click="form.file = null">✕</button></span>
            <FileDropzone v-else label="Загрузить файл" purpose="attachment" @uploaded="(f) => (form.file = pick(f[0]))" @error="(m) => (error = m)" />
          </div>
          <div v-if="form.kind === 'book'">
            <p class="field-label">Обложка</p>
            <MediaImg v-if="form.cover_url" :src="form.cover_url" alt="" class="h-32 border border-gold/30 object-cover" />
            <FileDropzone v-else label="Обложка" accept="image/*" purpose="image" @uploaded="(f) => (form.cover_url = f[0].url)" @error="(m) => (error = m)" />
          </div>
        </div>
        <div class="flex items-center gap-3">
          <button type="submit" class="btn-primary" :disabled="busy">Добавить</button>
          <button type="button" class="btn-ghost" @click="reset">Отмена</button>
          <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
        </div>
      </form>
    </div>

    <EmptyState v-if="!items.length">{{ isOwner ? 'Поделитесь книгами, ссылками и файлами' : 'Материалов пока нет' }}</EmptyState>

    <div class="space-y-14">
      <!-- Books -->
      <section v-if="books.length">
        <h3 class="mb-6 border-b border-gold/15 pb-3 text-3xl italic">Книги</h3>
        <div class="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <article v-for="m in books" :key="m.id" class="flex gap-5">
            <div class="frame frame-thin h-40 w-28 shrink-0">
              <div class="frame-inner flex items-center justify-center bg-gradient-to-b from-oxblood to-ink-900">
                <MediaImg v-if="m.cover_url" :src="m.cover_url" :alt="m.title" class="h-full w-full object-cover" />
                <span v-else class="px-2 text-center font-display text-sm italic leading-tight text-gold-light/80">{{ m.title }}</span>
              </div>
            </div>
            <div class="min-w-0">
              <p class="font-display text-xl italic leading-snug">{{ m.title }}</p>
              <p v-if="m.description" class="mt-2 line-clamp-4 text-sm text-parchment-muted">{{ m.description }}</p>
              <div class="mt-3 flex flex-wrap gap-3 font-caps text-sm font-semibold tracking-[0.12em]">
                <a v-if="m.file" :href="safeUrl(m.file.url)" :download="m.file.name" class="link">Скачать</a>
                <a v-if="m.url" :href="safeUrl(m.url)" target="_blank" rel="noopener nofollow" class="link">Открыть ↗</a>
                <button v-if="isOwner" type="button" class="text-parchment-faint hover:text-red-300" @click="remove(m)">Удалить</button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- Links -->
      <section v-if="links.length">
        <h3 class="mb-4 border-b border-gold/15 pb-3 text-3xl italic">Ссылки</h3>
        <ul class="divide-y divide-gold/10">
          <li v-for="m in links" :key="m.id" class="group flex items-start gap-4 py-4">
            <span class="mt-1 flex h-9 w-9 shrink-0 items-center justify-center border border-gold/40 text-gold">↗</span>
            <div class="min-w-0 flex-1">
              <a :href="safeUrl(m.url)" target="_blank" rel="noopener nofollow" class="font-display text-lg transition group-hover:text-gold-light">{{ m.title }}</a>
              <p class="truncate text-sm text-parchment-faint">{{ domain(m.url) }}</p>
              <p v-if="m.description" class="mt-1 text-parchment-muted">{{ m.description }}</p>
            </div>
            <button v-if="isOwner" type="button" class="text-sm text-parchment-faint hover:text-red-300" @click="remove(m)">✕</button>
          </li>
        </ul>
      </section>

      <!-- Files -->
      <section v-if="files.length">
        <h3 class="mb-4 border-b border-gold/15 pb-3 text-3xl italic">Файлы</h3>
        <ul class="divide-y divide-gold/10">
          <li v-for="m in files" :key="m.id" class="flex items-start gap-4 py-4">
            <span class="mt-1 flex h-11 w-11 shrink-0 items-center justify-center border border-gold/40 bg-ink-950/60 font-caps text-xs font-semibold tracking-wider text-gold">{{ fileExtension(m.file?.name) }}</span>
            <div class="min-w-0 flex-1">
              <p class="font-display text-lg">{{ m.title }}</p>
              <p class="text-sm text-parchment-faint">{{ m.file?.name }} · {{ formatSize(m.file?.size) }}</p>
              <p v-if="m.description" class="mt-1 text-parchment-muted">{{ m.description }}</p>
            </div>
            <a v-if="m.file" :href="safeUrl(m.file.url)" :download="m.file.name" class="btn-ghost text-sm">Скачать ↓</a>
            <button v-if="isOwner" type="button" class="text-sm text-parchment-faint hover:text-red-300" @click="remove(m)">✕</button>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Attachment, Material, Uploaded } from '~/utils/types'

const props = defineProps<{ initial: Material[]; isOwner: boolean }>()

const KIND_ONE = { book: 'Книга', link: 'Ссылка', file: 'Файл' } as const
const PLACEHOLDERS = { book: 'Учебник гармонии', link: 'Моя страница на IMSLP', file: 'Партии для квартета' } as const

const api = useApi()
const items = ref<Material[]>([...props.initial])
const books = computed(() => items.value.filter((m) => m.kind === 'book'))
const links = computed(() => items.value.filter((m) => m.kind === 'link'))
const files = computed(() => items.value.filter((m) => m.kind === 'file'))

const domain = (url?: string | null) => {
  try {
    return url ? new URL(url).hostname.replace(/^www\./, '') : ''
  } catch {
    return url || ''
  }
}

const empty = () => ({ kind: 'book' as Material['kind'], title: '', description: '', url: '', file: null as Attachment | null, cover_url: null as string | null })
const form = reactive(empty())
const adding = ref(false)
const busy = ref(false)
const error = ref('')
const pick = (u: Uploaded): Attachment => ({ url: u.url, name: u.name, content_type: u.content_type, size: u.size })
const reset = () => {
  Object.assign(form, empty())
  adding.value = false
  error.value = ''
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    const created = await api<Material>('/api/materials', {
      method: 'POST',
      body: {
        kind: form.kind,
        title: form.title,
        description: form.description || null,
        url: form.kind !== 'file' && form.url ? form.url : null,
        file: form.kind !== 'link' ? form.file : null,
        cover_url: form.kind === 'book' ? form.cover_url : null,
      },
    })
    items.value.unshift(created)
    reset()
  } catch (err) {
    error.value = apiError(err)
  } finally {
    busy.value = false
  }
}

async function remove(m: Material) {
  if (!confirm(`Удалить «${m.title}»?`)) return
  await api(`/api/materials/${m.id}`, { method: 'DELETE' })
  items.value = items.value.filter((x) => x.id !== m.id)
}
</script>
