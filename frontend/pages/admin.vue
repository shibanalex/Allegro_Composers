<template>
  <!-- For administrators: invitations and members -->
  <div class="mx-auto max-w-4xl">
    <PageHeader eyebrow="Allegro" title="Управление" subtitle="Приглашения в сообщество и участники." />

    <PageTabs :tabs="[{ id: 'invites', label: 'Приглашения', count: activeCount }, { id: 'members', label: 'Участники', count: users.length }, { id: 'roles', label: 'Права' }]" query="section">
      <template #invites>
        <form class="card mb-10 space-y-4" @submit.prevent="createInvite">
          <h2 class="text-2xl italic">Новое приглашение</h2>
          <div class="grid gap-4 sm:grid-cols-[minmax(0,1fr)_14rem]">
            <div>
              <label class="field-label" for="inv-note">Для кого (видите только вы)</label>
              <input id="inv-note" v-model="invite.note" class="field" maxlength="200" placeholder="Нина, скрипачка из консерватории">
            </div>
            <div>
              <label class="field-label" for="inv-role">Предложить роль</label>
              <select id="inv-role" v-model="invite.role" class="field">
                <option :value="null">— на выбор —</option>
                <option v-for="(r, id) in ROLES" :key="id" :value="id">{{ r.label }}</option>
              </select>
            </div>
          </div>
          <button type="submit" class="btn-primary" :disabled="busy">Создать ссылку</button>
          <div v-if="created" class="border border-gold/40 bg-gold/5 p-4">
            <p class="field-label">Ссылка-приглашение — покажется один раз</p>
            <div class="flex gap-2">
              <input :value="created" class="field font-mono text-sm" readonly @focus="($event.target as HTMLInputElement).select()">
              <button type="button" class="btn-secondary shrink-0 px-4 py-1.5 text-sm" @click="copy(created)">{{ copied ? 'Скопировано' : 'Копировать' }}</button>
            </div>
            <p class="mt-2 text-sm text-parchment-faint">Действует {{ ttlDays }} дней и только для одного человека. Отправьте её в личном сообщении.</p>
          </div>
          <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
        </form>

        <EmptyState v-if="!links.length">Приглашений ещё не было</EmptyState>
        <ul class="divide-y divide-gold/10">
          <li v-for="l in links" :key="l.id" class="flex flex-wrap items-center gap-x-4 gap-y-1 py-4">
            <span class="chip" :class="{ active: l.status === 'active' }">{{ LINK_STATUS[l.status] }}</span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-parchment">{{ l.purpose === 'reset' ? l.note : l.note || 'Приглашение' }}</span>
              <span class="block text-sm text-parchment-faint">
                {{ formatDate(l.created_at) }}
                <template v-if="l.role"> · роль: {{ ROLES[l.role]?.label }}</template>
                <template v-if="l.used_by"> · вступил(а): <NuxtLink :to="`/@${l.used_by.username}`" class="link">{{ l.used_by.display_name }}</NuxtLink></template>
                <template v-else-if="l.status === 'active'"> · до {{ formatDate(l.expires_at) }}</template>
              </span>
            </span>
            <button v-if="l.status === 'active'" type="button" class="btn-ghost text-sm hover:text-red-300" @click="revoke(l)">Отозвать</button>
          </li>
        </ul>
      </template>

      <template #members>
        <ul class="divide-y divide-gold/10">
          <li v-for="u in users" :key="u.id" class="flex flex-wrap items-center gap-4 py-4">
            <UserAvatar :user="u" :size="40" />
            <span class="min-w-0 flex-1">
              <NuxtLink :to="`/@${u.username}`" class="block truncate font-display italic text-parchment transition hover:text-gold-light">{{ u.display_name }}</NuxtLink>
              <span class="block text-sm text-parchment-faint">
                @{{ u.username }} · {{ ROLES[u.role || 'listener']?.label }} · с {{ formatDate(u.created_at) }}
                <template v-if="u.is_admin"> · <span class="text-gold">администратор</span></template>
                <template v-else-if="u.is_moderator"> · <span class="text-gold">модератор</span></template>
                <template v-if="u.is_hidden"> · <span class="text-red-300">в тени</span></template>
              </span>
            </span>
            <template v-if="u.id !== user?.id">
              <button type="button" class="btn-ghost text-sm" :title="u.is_hidden ? 'Вернуть на сайт' : 'Скрыть вместе со всем опубликованным (ничего не удаляется)'" @click="update(u, { is_hidden: !u.is_hidden })">
                {{ u.is_hidden ? 'Вернуть' : 'Скрыть' }}
              </button>
              <button v-if="!u.is_admin" type="button" class="btn-ghost text-sm" title="Может удалять чужие комментарии и записи" @click="update(u, { is_moderator: !u.is_moderator })">{{ u.is_moderator ? 'Снять модератора' : 'Сделать модератором' }}</button>
              <button type="button" class="btn-ghost text-sm" @click="update(u, { is_admin: !u.is_admin })">{{ u.is_admin ? 'Снять права' : 'Сделать админом' }}</button>
            </template>
            <button type="button" class="btn-ghost text-sm" title="Одноразовая ссылка, чтобы задать новый пароль" @click="resetLink(u)">Сброс пароля</button>
            <div v-if="resetFor === u.id && resetUrl" class="w-full border border-gold/40 bg-gold/5 p-3">
              <div class="flex gap-2">
                <input :value="resetUrl" class="field font-mono text-sm" readonly @focus="($event.target as HTMLInputElement).select()">
                <button type="button" class="btn-secondary shrink-0 px-4 py-1.5 text-sm" @click="copy(resetUrl)">{{ copied ? 'Скопировано' : 'Копировать' }}</button>
              </div>
              <p class="mt-2 text-sm text-parchment-faint">Отправьте ссылку участнику лично: по ней он задаст новый пароль. Действует двое суток.</p>
            </div>
          </li>
        </ul>
      </template>
      <!-- Who may do what: the table lives in the code (accounts/roles.py) -->
      <template #roles>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[40rem] text-left">
            <thead>
              <tr class="border-b border-gold/20 font-caps text-xs font-semibold tracking-[0.12em] text-gold">
                <th class="py-3 pr-4">Действие</th>
                <th v-for="c in ROLE_COLUMNS" :key="c.id" class="px-2 py-3 text-center">{{ c.label }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gold/10">
              <tr v-for="row in matrix || []" :key="row.capability">
                <td class="py-2.5 pr-4 font-elegant text-lg text-parchment">{{ row.label }}</td>
                <td v-for="c in ROLE_COLUMNS" :key="c.id" class="px-2 text-center" :class="row.who.includes(c.id) ? 'text-gold-light' : 'text-parchment-faint/40'">
                  {{ row.who.includes(c.id) ? '✓' : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="mt-4 text-sm text-parchment-faint">Роль участник выбирает сам в «Оформить зал». Модератора и администратора назначают здесь, во вкладке «Участники».</p>
      </template>
    </PageTabs>
  </div>
</template>

<script setup lang="ts">
import type { AccessLink, AdminUser, Role } from '~/utils/types'

definePageMeta({ middleware: 'admin' })
useSeoMeta({ title: 'Управление — Allegro', robots: 'noindex, nofollow' })

const LINK_STATUS: Record<string, string> = { active: 'Действует', used: 'Использовано', expired: 'Истекло', revoked: 'Отозвано' }
const ttlDays = 14

const api = useApi()
const { user } = useAuth()
const origin = useSiteOrigin()

const { data: linkData, refresh: refreshLinks } = await useAsyncData('admin-links', () => api<AccessLink[]>('/api/admin/links'))
const { data: userData, refresh: refreshUsers } = await useAsyncData('admin-users', () => api<AdminUser[]>('/api/admin/users'))
const links = computed(() => linkData.value || [])
const users = computed(() => userData.value || [])
const activeCount = computed(() => links.value.filter((l) => l.status === 'active' && l.purpose === 'invite').length)

const invite = reactive({ note: '', role: null as Role | null })
const created = ref('')
const busy = ref(false)
const error = ref('')
const copied = ref(false)

async function createInvite() {
  busy.value = true
  error.value = ''
  try {
    const link = await api<AccessLink>('/api/admin/invites', { method: 'POST', body: { note: invite.note || null, role: invite.role } })
    created.value = `${origin}/register?invite=${link.token}`
    invite.note = ''
    await refreshLinks()
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}

async function revoke(l: AccessLink) {
  if (!confirm('Отозвать приглашение? По ссылке больше нельзя будет зарегистрироваться.')) return
  await api(`/api/admin/links/${l.id}`, { method: 'DELETE' })
  await refreshLinks()
}

const ROLE_COLUMNS = [
  { id: 'listener', label: 'Слушатель' }, { id: 'performer', label: 'Исполнитель' }, { id: 'theorist', label: 'Теоретик' },
  { id: 'composer', label: 'Композитор' }, { id: 'moderator', label: 'Модератор' }, { id: 'admin', label: 'Админ' },
]
const { data: matrix } = await useAsyncData('roles-matrix', () => api<{ capability: string; label: string; who: string[] }[]>('/api/roles'))

async function update(u: AdminUser, body: { is_hidden?: boolean; is_admin?: boolean; is_moderator?: boolean }) {
  try {
    await api(`/api/admin/users/${u.id}`, { method: 'PATCH', body })
    await refreshUsers()
  } catch (e) {
    alert(apiError(e))
  }
}

const resetFor = ref('')
const resetUrl = ref('')
async function resetLink(u: AdminUser) {
  const link = await api<AccessLink>(`/api/admin/users/${u.id}/reset-link`, { method: 'POST' })
  resetFor.value = u.id
  resetUrl.value = `${origin}/reset?token=${link.token}`
  await refreshLinks()
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {}
}
</script>
