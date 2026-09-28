<template>
  <!-- Who the member is: composer, theorist, performer or listener (at sign-up and in «Оформить зал») -->
  <div class="grid gap-3 sm:grid-cols-2" role="radiogroup" :aria-label="label">
    <button
      v-for="(role, id) in ROLES"
      :key="id"
      type="button"
      role="radio"
      :aria-checked="modelValue === id"
      class="flex items-start gap-3 border p-4 text-left transition"
      :class="modelValue === id ? 'border-gold bg-gold/10' : 'border-gold/15 hover:border-gold/40'"
      @click="$emit('update:modelValue', id)"
    >
      <span class="mt-0.5 w-6 shrink-0 text-center font-display text-2xl text-gold">{{ role.icon }}</span>
      <span>
        <span class="block font-display text-lg" :class="modelValue === id ? 'text-gold-light' : 'text-parchment'">{{ role.label }}</span>
        <span class="block text-sm text-parchment-faint">{{ role.about }}</span>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ modelValue: string; label?: string }>(), { label: 'Роль' })
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
