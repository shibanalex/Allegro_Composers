<template>
  <div class="mx-auto max-w-3xl">
    <PageHeader eyebrow="Ваш зал" title="Оформить зал" />

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
        <p class="field-label">Кто вы на Allegro</p>
        <RolePicker v-model="form.role" />
        <p class="mt-2 text-sm text-parchment-faint">От роли зависят разделы зала и то, что можно публиковать. Сменить её можно в любой момент — опубликованное никуда не денется.</p>
      </div>

      <div>
        <p class="field-label">Стиль зала</p>
        <ThemePicker v-model="form.hall_theme" />
        <p class="mt-2 text-sm text-parchment-faint">Так ваш зал видят все. Стиль всего сайта для себя выбирается значком в шапке.</p>
      </div>

      <fieldset class="space-y-4 border-t border-gold/15 pt-8">
        <legend class="mb-2 w-full font-display text-3xl italic text-parchment">Убранство зала</legend>
        <HallSettingsEditor v-model="form.hall" :role="form.role" @error="(m) => { ok = false; message = m }" />
      </fieldset>

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

      <div>
        <label class="field-label" for="s-email">Email — необязательно</label>
        <input id="s-email" v-model="form.email" type="email" class="field" autocomplete="email" placeholder="чтобы восстановить доступ, если забудете пароль">
        <p class="mt-1 text-xs text-parchment-faint">Хранится только в зашифрованном виде и нигде не показывается.</p>
      </div>

      <div class="flex items-center gap-4 border-t border-gold/15 pt-6">
        <button type="submit" class="btn-primary" :disabled="busy">Сохранить</button>
        <NuxtLink :to="`/@${user?.username}`" class="btn-ghost">В зал</NuxtLink>
        <p v-if="message" class="text-sm" :class="ok ? 'text-gold-light' : 'text-red-300'">{{ message }}</p>
      </div>
    </form>

    <!-- Password -->
    <form class="mt-16 space-y-5 border-t border-gold/15 pt-10" @submit.prevent="changePassword">
      <h2 class="text-3xl italic">Пароль</h2>
      <div class="grid gap-5 sm:grid-cols-2">
        <div>
          <label class="field-label" for="s-pass-old">Текущий пароль</label>
          <input id="s-pass-old" v-model="password.current" type="password" class="field" autocomplete="current-password" required>
        </div>
        <div>
          <label class="field-label" for="s-pass-new">Новый пароль</label>
          <input id="s-pass-new" v-model="password.next" type="password" class="field" autocomplete="new-password" minlength="8" required>
        </div>
      </div>
      <div class="flex items-center gap-4">
        <button type="submit" class="btn-secondary" :disabled="password.busy">Сменить пароль</button>
        <p v-if="password.message" class="text-sm" :class="password.ok ? 'text-gold-light' : 'text-red-300'">{{ password.message }}</p>
      </div>
    </form>

    <!-- Sessions -->
    <section class="mt-16 space-y-4 border-t border-gold/15 pt-10">
      <h2 class="text-3xl italic">Устройства</h2>
      <p class="text-parchment-muted">Если вы входили с чужого компьютера или потеряли телефон — выйдите везде, кроме этого устройства.</p>
      <div class="flex items-center gap-4">
        <button type="button" class="btn-secondary" :disabled="sessions.busy" @click="signOutEverywhere">Выйти на всех устройствах</button>
        <p v-if="sessions.message" class="text-sm" :class="sessions.ok ? 'text-gold-light' : 'text-red-300'">{{ sessions.message }}</p>
      </div>
    </section>

    <!-- First-visit hints -->
    <section class="mt-16 space-y-4 border-t border-gold/15 pt-10">
      <h2 class="text-3xl italic">Подсказки</h2>
      <p class="text-parchment-muted">Короткие пояснения к кнопкам и разделам, которые показываются новичкам по одной.</p>
      <div class="flex items-center gap-4">
        <button type="button" class="btn-secondary" @click="showHintsAgain">Показать подсказки снова</button>
        <p v-if="hintsReset" class="text-sm text-gold-light">Подсказки появятся на страницах сайта</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { HallSettings, Me } from '~/utils/types'

definePageMeta({ middleware: 'auth' })
useSeoMeta({ title: 'Настройки зала — Allegro', robots: 'noindex, nofollow' })

const api = useApi()
const auth = useAuth()
const { user } = auth
const u = user.value!
const form = reactive({
  display_name: u.display_name,
  pseudonym: u.pseudonym || '',
  bio: u.bio || '',
  about_md: u.about_md || '',
  avatar_url: u.avatar_url || '',
  links: u.links.map((l) => ({ ...l })),
  role: u.role,
  hall_theme: u.hall_theme,
  hall: { ...(u.hall || {}) } as HallSettings,
  email: u.email || '',
})
const hints = useHints()
const hintsReset = ref(false)
async function showHintsAgain() {
  await hints.again()
  hintsReset.value = true
}
const busy = ref(false)
const message = ref('')
const ok = ref(false)

const password = reactive({ current: '', next: '', busy: false, message: '', ok: false })
async function changePassword() {
  password.busy = true
  password.message = ''
  try {
    await auth.changePassword(password.current, password.next)
    password.ok = true
    password.message = 'Пароль изменён, на других устройствах нужно войти заново'
    password.current = password.next = ''
  } catch (e) {
    password.ok = false
    password.message = apiError(e)
  } finally {
    password.busy = false
  }
}

const sessions = reactive({ busy: false, message: '', ok: false })
async function signOutEverywhere() {
  sessions.busy = true
  sessions.message = ''
  try {
    await auth.signOutEverywhere()
    sessions.ok = true
    sessions.message = 'Готово: остальные устройства вышли из аккаунта'
  } catch (e) {
    sessions.ok = false
    sessions.message = apiError(e)
  } finally {
    sessions.busy = false
  }
}

async function save() {
  busy.value = true
  message.value = ''
  try {
    user.value = await api<Me>('/api/users/me', {
      method: 'PATCH',
      body: { ...form, pseudonym: form.pseudonym || null, avatar_url: form.avatar_url || null, email: form.email.trim() },
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
