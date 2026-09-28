<template>
  <!-- A new password by a one-time link from an administrator (the site sends no letters) -->
  <div class="mx-auto max-w-md py-10">
    <PageHeader eyebrow="Allegro" title="Новый пароль" />

    <div v-if="!valid" class="card text-center font-elegant text-xl italic text-parchment-muted">
      Ссылка недействительна: её уже использовали или срок истёк. Попросите у администратора новую.
    </div>

    <form v-else class="card space-y-5" @submit.prevent="submit">
      <p class="font-elegant text-lg italic text-parchment-muted">Аккаунт @{{ check?.username }}</p>
      <div>
        <label class="field-label" for="password">Новый пароль</label>
        <input id="password" v-model="password" type="password" class="field" autocomplete="new-password" minlength="8" required>
      </div>
      <div>
        <label class="field-label" for="password2">Ещё раз</label>
        <input id="password2" v-model="password2" type="password" class="field" autocomplete="new-password" minlength="8" required>
      </div>
      <button type="submit" class="btn-primary w-full" :disabled="busy">Сохранить и войти</button>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </form>
  </div>
</template>

<script setup lang="ts">
useSeoMeta({ title: 'Новый пароль — Allegro', robots: 'noindex, nofollow' })

const route = useRoute()
const api = useApi()
const { resetPassword } = useAuth()
const token = typeof route.query.token === 'string' ? route.query.token : ''

const { data: check } = await useAsyncData(`reset-${token}`, () =>
  token ? api<{ valid: boolean; purpose?: string; username?: string | null }>(`/api/auth/links/${token}`) : Promise.resolve(null),
)
const valid = computed(() => !!check.value?.valid && check.value.purpose === 'reset')

const password = ref('')
const password2 = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  if (password.value !== password2.value) {
    error.value = 'Пароли не совпадают'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await resetPassword(token, password.value)
    await navigateTo(`/@${check.value?.username}`)
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
