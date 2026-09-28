<template>
  <!-- «Нравится» on a work, a performance or a post: answers at once, then confirms with the server -->
  <button
    type="button"
    class="inline-flex items-center gap-1.5 transition"
    :class="state.mine ? 'text-gold-light' : 'text-parchment-faint hover:text-gold-light'"
    :aria-pressed="state.mine"
    :title="can('react') ? (state.mine ? 'Больше не нравится' : 'Нравится') : 'Войдите, чтобы отметить'"
    :disabled="busy"
    @click="toggle"
  >
    <span class="text-lg leading-none" aria-hidden="true">{{ state.mine ? '♥' : '♡' }}</span>
    <span>{{ state.count || (compact ? '' : 'Нравится') }}</span>
  </button>
</template>

<script setup lang="ts">
import type { Reactions } from '~/utils/types'

const props = defineProps<{ kind: 'opus' | 'post' | 'performance'; id: string; value?: Reactions | null; compact?: boolean }>()

const api = useApi()
const { can } = useAuth()
const state = reactive<Reactions>({ count: props.value?.count ?? 0, mine: props.value?.mine ?? false })
watch(() => props.value, (v) => v && Object.assign(state, v))
const busy = ref(false)

async function toggle() {
  if (!can('react')) return navigateTo('/login')
  const before = { ...state }
  state.mine = !state.mine
  state.count += state.mine ? 1 : -1
  busy.value = true
  try {
    Object.assign(state, await api<Reactions>(`/api/reactions/${props.kind}/${props.id}`, { method: state.mine ? 'PUT' : 'DELETE' }))
  } catch {
    Object.assign(state, before)
  } finally {
    busy.value = false
  }
}
</script>
