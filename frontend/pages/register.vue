<template>
  <div class="mx-auto max-w-2xl py-10">
    <PageHeader eyebrow="Allegro" title="Открыть свой зал" subtitle="Сообщество композиторов, теоретиков, исполнителей и слушателей." />

    <!-- Invitations only, and there is no (valid) invitation in the link -->
    <div v-if="needsInvite" class="card text-center">
      <p class="font-elegant text-xl italic text-parchment-muted">
        {{ invite ? 'Это приглашение уже использовали, отозвали или срок его истёк.' : 'Сейчас в Allegro можно войти только по приглашению.' }}
      </p>
      <p class="mt-3 text-parchment-faint">Приглашение — это ссылка, которую присылает администратор сообщества.</p>
      <p class="mt-6"><NuxtLink to="/login" class="link">Войти</NuxtLink> · <NuxtLink to="/about?tab=feedback" class="link">Написать нам</NuxtLink></p>
    </div>

    <form v-else class="card space-y-6" @submit.prevent="submit">
      <p v-if="check?.inviter" class="font-elegant text-lg italic text-parchment-muted">Вас пригласил(а) {{ check.inviter }}.</p>

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
const api = useApi()
const { register, config, registrationOpen } = useAuth()
const invite = typeof route.query.invite === 'string' ? route.query.invite : ''

// Is the invitation in the link still valid (and which role does it suggest)
const { data: check } = await useAsyncData(`invite-${invite}`, () =>
  invite ? api<{ valid: boolean; purpose?: string; role?: string | null; inviter?: string | null }>(`/api/auth/links/${invite}`) : Promise.resolve(null),
)
const validInvite = computed(() => !!check.value?.valid && check.value.purpose === 'invite')
const needsInvite = computed(() => config.value?.registration === 'closed' || (!registrationOpen.value && !validInvite.value))

const form = reactive({ display_name: '', username: '', password: '', role: check.value?.role || 'composer', email: '' })
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
      invite: validInvite.value ? invite : null,
    })
    await navigateTo(safeNext(route.query.next, `/@${form.username.trim().toLowerCase()}`))
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
