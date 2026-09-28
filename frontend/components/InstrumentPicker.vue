<template>
  <!-- The instruments of a work: chips to remove, a field with suggestions to add (the same name may repeat) -->
  <div>
    <div class="flex flex-wrap items-center gap-2">
      <span v-for="(name, i) in modelValue" :key="`${name}-${i}`" class="chip gap-1.5 !pr-1">
        {{ name }}
        <button type="button" class="px-1 text-parchment-faint transition hover:text-red-300" :aria-label="`Убрать: ${name}`" @click="remove(i)">×</button>
      </span>
      <div class="flex items-center gap-1">
        <input
          v-model="draft"
          class="field w-44 py-1 text-sm"
          :list="listId"
          placeholder="+ инструмент"
          aria-label="Добавить инструмент"
          @keydown.enter.prevent="add"
          @change="add"
        >
        <datalist :id="listId"><option v-for="name in INSTRUMENTS" :key="name" :value="name" /></datalist>
      </div>
    </div>
    <p v-if="!modelValue.length" class="mt-2 text-sm italic text-parchment-faint">Состав не указан — добавьте инструменты</p>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ modelValue: string[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>()

const listId = useId()
const draft = ref('')

function add() {
  const name = draft.value.trim().toLowerCase()
  if (!name) return
  emit('update:modelValue', [...props.modelValue, name].slice(0, 30))
  draft.value = ''
}

function remove(i: number) {
  emit('update:modelValue', props.modelValue.filter((_, j) => j !== i))
}
</script>
