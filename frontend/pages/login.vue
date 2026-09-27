<template>
  <div class="mx-auto max-w-md py-10">
    <PageHeader eyebrow="Allegro" title="Вход" />
    <form class="card space-y-5" @submit.prevent="submit">
      <div>
        <label class="field-label" for="login">Имя пользователя или email</label>
        <input id="login" v-model="form.login" class="field" autocomplete="username" required>
      </div>
      <div>
        <label class="field-label" for="password">Пароль</label>
        <input id="password" v-model="form.password" type="password" class="field" autocomplete="current-password" required>
      </div>
      <button type="submit" class="btn-primary w-full" :disabled="busy">Войти</button>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </form>
    <p class="mt-6 text-center font-elegant text-lg italic text-parchment-muted">
      <template v-if="registrationOpen">Ещё нет своего зала? <NuxtLink :to="`/register?next=${encodeURIComponent(next)}`" class="link">Открыть</NuxtLink></template>
      <template v-else-if="setupAvailable">Сайт только что запущен? <NuxtLink to="/setup" class="link">Первая настройка</NuxtLink></template>
      <template v-else>Сообщество пока открыто только по приглашениям</template>
    </p>
  </div>
</template>

<script setup lang="ts">
useSeoMeta({ title: 'Вход — Allegro', robots: 'noindex, nofollow' })

const route = useRoute()
const { login, registrationOpen, setupAvailable } = useAuth()
const next = computed(() => safeNext(route.query.next))
const form = reactive({ login: '', password: '' })
const busy = ref(false)
const error = ref('')

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await login(form.login, form.password)
    await navigateTo(next.value)
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
