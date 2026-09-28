<template>
  <!-- First start of a freshly deployed site: create the owner's account once, with the code from the hosting settings -->
  <div class="mx-auto max-w-md py-10">
    <PageHeader eyebrow="Allegro" title="Первый запуск" subtitle="Создайте аккаунт владельца. После этого страница закроется навсегда." />

    <div v-if="!setupAvailable" class="card text-center font-elegant text-xl italic text-parchment-muted">
      Сайт уже настроен. <NuxtLink to="/login" class="link">Войти</NuxtLink>
    </div>

    <form v-else class="card space-y-5" @submit.prevent="submit">
      <div>
        <label class="field-label" for="code">Код настройки</label>
        <input id="code" v-model="form.code" type="password" class="field" autocomplete="off" required>
        <p class="mt-1 text-xs text-parchment-faint">Тот, что вы вписали в SETUP_TOKEN в настройках хостинга</p>
      </div>
      <div>
        <label class="field-label" for="username">Имя пользователя</label>
        <div class="flex items-center border border-ink-600 bg-ink-950/70 focus-within:border-gold/70">
          <span class="pl-4 text-parchment-faint">allegro/@</span>
          <input id="username" v-model="form.username" class="w-full bg-transparent py-2.5 pr-4 text-parchment outline-none" pattern="[a-z0-9_]{3,32}" autocomplete="username" required>
        </div>
        <p class="mt-1 text-xs text-parchment-faint">То же, что в LOGIN_ALLOWLIST</p>
      </div>
      <div>
        <label class="field-label" for="display_name">Имя на сайте</label>
        <input id="display_name" v-model="form.display_name" class="field" required>
      </div>
      <div>
        <label class="field-label" for="email">Email</label>
        <input id="email" v-model="form.email" type="email" class="field" autocomplete="email" required>
      </div>
      <div>
        <label class="field-label" for="password">Пароль</label>
        <input id="password" v-model="form.password" type="password" class="field" autocomplete="new-password" minlength="12" required>
        <p class="mt-1 text-xs text-parchment-faint">Не короче 12 символов. Надёжнее всего — несколько слов, например «зимний-ноктюрн-в-ля-миноре»</p>
      </div>
      <div>
        <label class="field-label" for="password2">Пароль ещё раз</label>
        <input id="password2" v-model="password2" type="password" class="field" autocomplete="new-password" minlength="12" required>
      </div>
      <button type="submit" class="btn-primary w-full" :disabled="busy">Создать аккаунт</button>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </form>
  </div>
</template>

<script setup lang="ts">
useSeoMeta({ title: 'Первый запуск — Allegro', robots: 'noindex, nofollow' })

const { setup, setupAvailable } = useAuth()
const form = reactive({ code: '', username: '', display_name: '', email: '', password: '', role: 'composer' })
const password2 = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  if (form.password !== password2.value) {
    error.value = 'Пароли не совпадают'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await setup({ ...form, username: form.username.trim().toLowerCase() })
    await navigateTo('/settings')
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
