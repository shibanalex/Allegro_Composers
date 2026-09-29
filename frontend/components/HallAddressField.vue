<template>
  <!-- The hall's address at sign-up: checked as it is typed, with what exactly is wrong and free variants -->
  <div>
    <label class="field-label" for="username">Адрес зала</label>
    <div class="flex items-center border bg-ink-950/70 transition focus-within:border-gold/70" :class="state === 'bad' ? 'border-red-400/60' : state === 'ok' ? 'border-gold/50' : 'border-ink-600'">
      <span class="pl-4 text-parchment-faint">allegro/@</span>
      <input
        id="username"
        :value="modelValue"
        class="w-full bg-transparent py-2.5 pr-4 text-parchment outline-none"
        placeholder="ivan_petrov"
        autocomplete="username"
        autocapitalize="none"
        spellcheck="false"
        required
        @input="type(($event.target as HTMLInputElement).value)"
      >
      <span class="pr-3 text-lg" aria-hidden="true">{{ state === 'ok' ? '✓' : state === 'bad' ? '✕' : '' }}</span>
    </div>

    <p v-if="state === 'ok'" class="mt-1 text-sm text-gold-light">Адрес свободен</p>
    <ul v-else-if="state === 'bad'" class="mt-1 space-y-0.5 text-sm text-red-300" aria-live="polite">
      <li v-for="p in problems" :key="p">• {{ p }}</li>
    </ul>
    <p v-else class="mt-1 text-xs text-parchment-faint">Латинские буквы, цифры, точка, дефис и _ — от 3 до 32 знаков</p>

    <p v-if="state === 'bad' && suggestions.length" class="mt-2 flex flex-wrap items-center gap-2 text-sm text-parchment-muted">
      Можно взять:
      <button v-for="s in suggestions" :key="s" type="button" class="chip" @click="take(s)">{{ s }}</button>
    </p>
  </div>
</template>

<script setup lang="ts">
interface Check { ok: boolean; problems: string[]; suggestions: string[] }

const props = defineProps<{ modelValue: string; name?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; 'update:valid': [value: boolean] }>()

const api = useApi()
const problems = ref<string[]>([])
const suggestions = ref<string[]>([])
const state = ref<'idle' | 'ok' | 'bad'>('idle')
// Until the address is typed by hand, it follows the name: «Иван Петров» → ivan_petrov
const touched = ref(!!props.modelValue)

let timer: ReturnType<typeof setTimeout> | undefined
let requestId = 0
function check(value: string) {
  clearTimeout(timer)
  if (!value.trim()) {
    state.value = 'idle'
    emit('update:valid', false)
    return
  }
  timer = setTimeout(async () => {
    const id = ++requestId
    try {
      const r = await api<Check>('/api/auth/username', { params: { value } })
      if (id !== requestId) return
      problems.value = r.problems
      suggestions.value = r.suggestions
      state.value = r.ok ? 'ok' : 'bad'
      emit('update:valid', r.ok)
    } catch {
      state.value = 'idle'
    }
  }, 300)
}

function type(value: string) {
  touched.value = true
  emit('update:modelValue', value)
  check(value)
}
function take(value: string) {
  touched.value = true
  emit('update:modelValue', value)
  check(value)
}

watch(() => props.name, async (name) => {
  if (touched.value || !name?.trim()) return
  try {
    const r = await api<Check>('/api/auth/username', { params: { value: name } })
    if (touched.value) return
    const value = r.ok ? name.trim().toLowerCase() : r.suggestions[0]
    if (value) {
      emit('update:modelValue', value)
      check(value)
    }
  } catch {}
})
</script>
