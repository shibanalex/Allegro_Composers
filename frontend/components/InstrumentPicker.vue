<template>
  <!-- The instruments of a work: each once, with how many (a quartet has two violins); suggestions as you type -->
  <div>
    <ul v-if="rows.length" class="mb-3 flex flex-wrap gap-2">
      <li v-for="row in rows" :key="row.name" class="flex items-center border border-gold/30 bg-ink-950/50">
        <span class="px-3 py-1 font-elegant text-lg text-parchment">{{ row.name }}</span>
        <span v-if="row.count > 1" class="pr-2 font-mono text-sm text-gold-light">× {{ row.count }}</span>
        <button type="button" class="border-l border-gold/20 px-2 py-1 text-parchment-faint transition hover:text-gold-light" :aria-label="`Меньше: ${row.name}`" @click="less(row.name)">−</button>
        <button type="button" class="border-l border-gold/20 px-2 py-1 text-parchment-faint transition hover:text-gold-light" :aria-label="`Больше: ${row.name}`" @click="more(row.name)">+</button>
        <button type="button" class="border-l border-gold/20 px-2 py-1 text-parchment-faint transition hover:text-red-300" :aria-label="`Убрать: ${row.name}`" @click="drop(row.name)">✕</button>
      </li>
    </ul>
    <p v-else class="mb-3 text-sm italic text-parchment-faint">Состав не указан — добавьте инструменты</p>

    <div ref="root" class="relative w-full max-w-sm">
      <input
        v-model="draft"
        class="field py-1.5"
        placeholder="+ добавить инструмент"
        aria-label="Добавить инструмент"
        autocomplete="off"
        @focus="open = true"
        @keydown.down.prevent="pick(1)"
        @keydown.up.prevent="pick(-1)"
        @keydown.enter.prevent="add(suggestions[active] || draft)"
        @keydown.esc="open = false"
      >
      <ul v-if="open && suggestions.length" class="absolute left-0 right-0 top-full z-30 mt-1 max-h-60 overflow-y-auto border border-gold/25 bg-ink-900/95 py-1 shadow-2xl shadow-black">
        <li v-for="(name, i) in suggestions" :key="name">
          <button
            type="button"
            class="block w-full px-3 py-1.5 text-left font-elegant text-lg transition"
            :class="i === active ? 'bg-gold/15 text-gold-light' : 'text-parchment hover:bg-gold/5'"
            @mouseenter="active = i"
            @click="add(name)"
          >
            {{ name }}<span v-if="counts[name]" class="ml-2 text-sm text-parchment-faint">уже {{ counts[name] }}</span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ modelValue: string[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>()

const draft = ref('')
const open = ref(false)
const active = ref(0)
const root = ref<HTMLElement>()

const counts = computed(() => {
  const c: Record<string, number> = {}
  for (const name of props.modelValue) c[name] = (c[name] || 0) + 1
  return c
})
// Each instrument once, in the order it first appears
const rows = computed(() => [...new Set(props.modelValue)].map((name) => ({ name, count: counts.value[name] })))

const suggestions = computed(() => {
  const q = draft.value.trim().toLowerCase().replace(/ё/g, 'е')
  const list = q ? INSTRUMENTS.filter((name) => name.includes(q)) : INSTRUMENTS.filter((name) => !counts.value[name])
  // what was typed, if it isn't one of the suggestions: an instrument of one's own
  if (q && !INSTRUMENTS.includes(q)) list.push(q)
  return list.slice(0, 12)
})
watch(draft, () => (active.value = 0))

const set = (list: string[]) => emit('update:modelValue', list.slice(0, 30))

function add(name: string) {
  name = name.trim().toLowerCase()
  if (!name) return
  set([...props.modelValue, name])
  draft.value = ''
  open.value = false
}
function more(name: string) {
  const list = [...props.modelValue]
  list.splice(list.lastIndexOf(name) + 1, 0, name) // next to the same instrument
  set(list)
}
function less(name: string) {
  const list = [...props.modelValue]
  list.splice(list.lastIndexOf(name), 1)
  set(list)
}
function drop(name: string) {
  set(props.modelValue.filter((x) => x !== name))
}
function pick(step: number) {
  open.value = true
  if (suggestions.value.length) active.value = (active.value + step + suggestions.value.length) % suggestions.value.length
}

const onDocClick = (e: MouseEvent) => {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>
