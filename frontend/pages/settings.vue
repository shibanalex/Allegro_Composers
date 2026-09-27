<template>
  <div class="mx-auto max-w-3xl">
    <PageHeader eyebrow="Ваш зал" title="Настройки" />

    <form class="space-y-8" @submit.prevent="save">
      <div class="grid gap-8 sm:grid-cols-[12rem_minmax(0,1fr)]">
        <div>
          <p class="field-label">Портрет</p>
          <div class="portrait mx-auto h-56 w-44">
            <img v-if="form.avatar_url" :src="form.avatar_url" alt="">
            <div v-else class="flex items-center justify-center bg-ink-700 font-display text-5xl italic text-gold/50">{{ initials(form.display_name) }}</div>
          </div>
          <FileDropzone class="mt-4" label="Сменить" hint="JPG, PNG" accept="image/*" purpose="image" @uploaded="(f) => (form.avatar_url = f[0].url)" @error="(m) => (message = m)" />
        </div>

        <div class="space-y-5">
          <div>
            <label class="field-label" for="s-name">Имя</label>
            <input id="s-name" v-model="form.display_name" class="field" required maxlength="120">
          </div>
          <div>
            <label class="field-label" for="s-pseudo">Творческий псевдоним</label>
            <input id="s-pseudo" v-model="form.pseudonym" class="field" maxlength="120" placeholder="Если выступаете под творческим именем">
          </div>
          <div>
            <label class="field-label" for="s-bio">Манифест — 2–3 строки в шапке зала</label>
            <textarea id="s-bio" v-model="form.bio" rows="3" maxlength="400" class="field resize-y font-elegant text-lg italic" placeholder="Композитор, исследователь фортепианной полифонии…" />
          </div>
        </div>
      </div>

      <div>
        <label class="field-label" for="s-about">О себе — биография, исполненные сочинения, инструментарий (Markdown)</label>
        <textarea id="s-about" v-model="form.about_md" rows="12" class="field resize-y" />
      </div>

      <div>
        <p class="field-label">Ссылки — контакты, партитуры, аудиоплатформы</p>
        <div v-for="(l, i) in form.links" :key="i" class="mb-2 flex gap-2">
          <input v-model="l.label" class="field w-40" placeholder="YouTube" required>
          <input v-model="l.url" class="field" placeholder="https://…" required>
          <button type="button" class="btn-ghost px-3" aria-label="Убрать" @click="form.links.splice(i, 1)">✕</button>
        </div>
        <button type="button" class="link font-caps text-sm font-semibold tracking-[0.15em]" @click="form.links.push({ label: '', url: '' })">+ Добавить ссылку</button>
      </div>

      <div class="flex items-center gap-4 border-t border-gold/15 pt-6">
        <button type="submit" class="btn-primary" :disabled="busy">Сохранить</button>
        <NuxtLink :to="`/@${user?.username}`" class="btn-ghost">В зал</NuxtLink>
        <p v-if="message" class="text-sm" :class="ok ? 'text-gold-light' : 'text-red-300'">{{ message }}</p>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import type { Me } from '~/utils/types'

definePageMeta({ middleware: 'auth' })
useSeoMeta({ title: 'Настройки зала — Allegro' })

const api = useApi()
const { user } = useAuth()
const u = user.value!
const form = reactive({
  display_name: u.display_name,
  pseudonym: u.pseudonym || '',
  bio: u.bio || '',
  about_md: u.about_md || '',
  avatar_url: u.avatar_url || '',
  links: u.links.map((l) => ({ ...l })),
})
const busy = ref(false)
const message = ref('')
const ok = ref(false)

async function save() {
  busy.value = true
  message.value = ''
  try {
    user.value = await api<Me>('/api/users/me', {
      method: 'PATCH',
      body: { ...form, pseudonym: form.pseudonym || null, avatar_url: form.avatar_url || null },
    })
    ok.value = true
    message.value = 'Сохранено'
  } catch (e) {
    ok.value = false
    message.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
