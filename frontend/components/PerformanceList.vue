<template>
  <!-- «Исполнения»: all members' (main page), one performer's (their hall) or of one work (its page) -->
  <div class="mx-auto max-w-3xl">
    <div v-if="canAdd && !formOpen" class="mb-8 flex justify-end">
      <button type="button" class="btn-primary px-4 py-1.5 text-sm" @click="openForm(null)">+ Исполнение</button>
    </div>
    <PerformanceForm v-if="formOpen" :key="editing?.id || 'new'" :editing="editing" :opus-id="opusId" class="mb-10" @saved="onSaved" @cancel="formOpen = false" />

    <EmptyState v-if="!items.length && !formOpen">{{ emptyText }}</EmptyState>
    <div class="space-y-6">
      <PerformanceCard
        v-for="p in items"
        :key="p.id"
        :performance="p"
        :show-performer="!performer"
        :is-owner="user?.id === p.performer.id"
        @edit="openForm"
        @remove="remove"
      />
    </div>
    <div v-if="items.length < total" class="mt-8 text-center">
      <button class="btn-secondary" :disabled="loading" @click="more">Ещё исполнения</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Page, Performance } from '~/utils/types'

const props = defineProps<{ performer?: string; opus?: string; opusId?: string | null; emptyText?: string }>()

const api = useApi()
const { user, can } = useAuth()
const canAdd = computed(() => can('publish_performance') && (!props.performer || user.value?.username === props.performer))

const params = computed(() => ({ ...(props.performer ? { performer: props.performer } : {}), ...(props.opus ? { opus: props.opus } : {}) }))
const { data } = await useAsyncData(`performances-${props.performer || ''}-${props.opus || ''}`, () =>
  api<Page<Performance>>('/api/performances', { params: { ...params.value, limit: 20 } }),
)
const items = ref<Performance[]>(data.value?.items || [])
const total = ref(data.value?.total || 0)
watch(data, (d) => {
  items.value = d?.items || []
  total.value = d?.total || 0
})
const loading = ref(false)

async function more() {
  loading.value = true
  try {
    const page = await api<Page<Performance>>('/api/performances', { params: { ...params.value, limit: 20, offset: items.value.length } })
    items.value.push(...page.items)
    total.value = page.total
  } finally {
    loading.value = false
  }
}

const formOpen = ref(false)
const editing = ref<Performance | null>(null)
function openForm(p: Performance | null) {
  editing.value = p
  formOpen.value = true
}
function onSaved(saved: Performance) {
  const i = items.value.findIndex((p) => p.id === saved.id)
  if (i >= 0) items.value[i] = saved
  else {
    items.value.unshift(saved)
    total.value += 1
  }
  formOpen.value = false
}
async function remove(p: Performance) {
  if (!confirm(`Удалить исполнение «${p.title}»?`)) return
  await api(`/api/performances/${p.id}`, { method: 'DELETE' })
  items.value = items.value.filter((x) => x.id !== p.id)
  total.value -= 1
}
</script>
