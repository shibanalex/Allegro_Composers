<template>
  <div class="mx-auto max-w-3xl">
    <PageHeader eyebrow="Сборники и циклы" :title="editing ? 'Редактирование сборника' : 'Новый сборник'" />

    <form class="space-y-6" @submit.prevent="save">
      <div class="grid gap-5 sm:grid-cols-[minmax(0,1fr)_8rem]">
        <div>
          <label class="field-label" for="c-title">Название</label>
          <input id="c-title" v-model="form.title" class="field text-xl" required placeholder="Цикл «Флориография»">
        </div>
        <div>
          <label class="field-label" for="c-year">Год</label>
          <input id="c-year" v-model.number="form.year" type="number" class="field">
        </div>
      </div>
      <div>
        <label class="field-label" for="c-desc">Описание</label>
        <textarea id="c-desc" v-model="form.description" rows="3" class="field resize-y" />
      </div>

      <div>
        <p class="field-label">Опусы — в порядке исполнения</p>
        <EmptyState v-if="!opuses.length">Сначала опубликуйте хотя бы один опус</EmptyState>
        <ul class="divide-y divide-gold/10 border-y border-gold/15">
          <li v-for="o in ordered" :key="o.id" class="flex items-center gap-3 py-3">
            <input :id="`o-${o.id}`" v-model="selected" type="checkbox" :value="o.id" class="accent-[#c9a36a]">
            <label :for="`o-${o.id}`" class="min-w-0 flex-1 cursor-pointer truncate">
              <span class="font-display">{{ o.title }}</span>
              <span v-if="o.subtitle" class="text-sm italic text-parchment-faint"> · {{ o.subtitle }}</span>
            </label>
            <template v-if="selected.includes(o.id)">
              <button type="button" class="btn-ghost px-2" aria-label="Выше" @click="move(o.id, -1)">↑</button>
              <button type="button" class="btn-ghost px-2" aria-label="Ниже" @click="move(o.id, 1)">↓</button>
            </template>
          </li>
        </ul>
      </div>

      <div class="flex flex-wrap items-center gap-4 border-t border-gold/15 pt-6">
        <button type="submit" class="btn-primary" :disabled="busy">Сохранить</button>
        <button v-if="editing" type="button" class="btn-ghost hover:text-red-300" @click="remove">Удалить сборник</button>
        <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import type { Collection, Opus, Page } from '~/utils/types'

definePageMeta({ middleware: 'auth' })
useSeoMeta({ title: 'Сборник — Allegro' })

const route = useRoute()
const api = useApi()
const { user } = useAuth()
const editing = typeof route.query.edit === 'string' ? route.query.edit : null

const form = reactive({ title: '', description: '', year: new Date().getFullYear() as number | null })
const selected = ref<string[]>([])
const busy = ref(false)
const error = ref('')

const { data: mine } = await useAsyncData('collection-opuses', () => api<Page<Opus>>('/api/opuses', { params: { mine: true, limit: 100 } }))
const opuses = computed(() => mine.value?.items || [])
// Selected works first, in their chosen order
const ordered = computed(() => [
  ...selected.value.map((id) => opuses.value.find((o) => o.id === id)!).filter(Boolean),
  ...opuses.value.filter((o) => !selected.value.includes(o.id)),
])

if (editing) {
  const collections = await api<Collection[]>('/api/collections', { params: { author: user.value!.username } })
  const c = collections.find((x) => x.id === editing)
  if (c) {
    Object.assign(form, { title: c.title, description: c.description || '', year: c.year })
    selected.value = c.opuses.map((o) => o.id)
  }
}

const move = (id: string, d: number) => {
  const i = selected.value.indexOf(id)
  const j = i + d
  if (j < 0 || j >= selected.value.length) return
  const next = [...selected.value]
  ;[next[i], next[j]] = [next[j], next[i]]
  selected.value = next
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    const body = { ...form, description: form.description || null, opus_ids: selected.value }
    if (editing) await api(`/api/collections/${editing}`, { method: 'PATCH', body })
    else await api('/api/collections', { method: 'POST', body })
    await navigateTo(`/@${user.value!.username}?tab=collections`)
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!confirm('Удалить сборник? Сами опусы останутся.')) return
  await api(`/api/collections/${editing}`, { method: 'DELETE' })
  await navigateTo(`/@${user.value!.username}?tab=collections`)
}
</script>
