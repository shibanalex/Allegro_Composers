<template>
  <div class="mx-auto max-w-2xl py-10">
    <PageHeader eyebrow="Allegro" title="Открыть свой зал" subtitle="Сообщество композиторов, теоретиков, исполнителей и слушателей." />

    <form class="card space-y-6" @submit.prevent="submit">
      <div class="grid gap-5 sm:grid-cols-2">
        <div>
          <label class="field-label" for="display_name">Имя</label>
          <input id="display_name" v-model="form.display_name" class="field" placeholder="Имя и фамилия" required maxlength="120">
        </div>
        <HallAddressField v-model="form.username" :name="form.display_name" />
        <div>
          <label class="field-label" for="password">Пароль</label>
          <input id="password" v-model="form.password" type="password" class="field" autocomplete="new-password" minlength="8" required>
        </div>
        <div>
          <label class="field-label" for="password2">Пароль ещё раз</label>
          <input id="password2" v-model="password2" type="password" class="field" autocomplete="new-password" minlength="8" required>
        </div>
      </div>

      <div>
        <p class="field-label">Кто вы</p>
        <RolePicker v-model="form.role" />
        <p class="mt-2 text-sm text-parchment-faint">Роль можно сменить потом в своём зале.</p>
      </div>

      <div>
        <label class="field-label" for="email">Email — необязательно</label>
        <input id="email" v-model="form.email" type="email" class="field" autocomplete="email" placeholder="чтобы восстановить доступ, если забудете пароль">
        <p class="mt-1 text-xs text-parchment-faint">Хранится только в зашифрованном виде и нигде не показывается. Телефон не нужен.</p>
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
useSeoMeta({ title: 'Регистрация — Allegro', robots: 'noindex, nofollow' })

const route = useRoute()
const { register } = useAuth()

const form = reactive({ display_name: '', username: '', password: '', role: 'composer', email: '' })
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
    await register({
      ...form,
      username: form.username.trim().toLowerCase(),
      email: form.email.trim() || null,
    })
    await navigateTo(safeNext(route.query.next, `/@${form.username.trim().toLowerCase()}`))
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
