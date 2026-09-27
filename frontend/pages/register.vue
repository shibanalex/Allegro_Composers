<template>
  <div class="mx-auto max-w-md py-10">
    <PageHeader eyebrow="Allegro" title="Открыть свой зал" subtitle="Выставка ваших произведений, блог и материалы — солидно перед музыкантами и комиссиями." />
    <form class="card space-y-5" @submit.prevent="submit">
      <div>
        <label class="field-label" for="display_name">Имя</label>
        <input id="display_name" v-model="form.display_name" class="field" placeholder="Имя и фамилия" required>
      </div>
      <div>
        <label class="field-label" for="username">Адрес зала</label>
        <div class="flex items-center border border-ink-600 bg-ink-950/70 focus-within:border-gold/70">
          <span class="pl-4 text-parchment-faint">allegro/@</span>
          <input id="username" v-model="form.username" class="w-full bg-transparent py-2.5 pr-4 text-parchment outline-none" pattern="[a-z0-9_]{3,32}" placeholder="imya_familiya" required>
        </div>
        <p class="mt-1 text-xs text-parchment-faint">3–32 символа: латиница, цифры и _</p>
      </div>
      <div>
        <label class="field-label" for="email">Email</label>
        <input id="email" v-model="form.email" type="email" class="field" autocomplete="email" required>
      </div>
      <div>
        <label class="field-label" for="password">Пароль</label>
        <input id="password" v-model="form.password" type="password" class="field" autocomplete="new-password" minlength="8" required>
      </div>
      <button type="submit" class="btn-primary w-full" :disabled="busy">Открыть зал</button>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </form>
    <p class="mt-6 text-center font-elegant text-lg italic text-parchment-muted">
      Уже есть зал? <NuxtLink to="/login" class="link">Войти</NuxtLink>
    </p>
  </div>
</template>

<script setup lang="ts">
useSeoMeta({ title: 'Регистрация — Allegro' })

const route = useRoute()
const { register } = useAuth()
const form = reactive({ display_name: '', username: '', email: '', password: '' })
const busy = ref(false)
const error = ref('')

watch(() => form.username, (v) => (form.username = v.toLowerCase().replace(/[^a-z0-9_]/g, '')))

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await register({ ...form })
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : `/@${form.username}`
    await navigateTo(next)
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
