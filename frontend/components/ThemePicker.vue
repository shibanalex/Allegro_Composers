<template>
  <!-- The style of a hall: each card is a small sample of it, drawn with the style itself -->
  <div class="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="Стиль зала">
    <button
      v-for="(theme, id) in HALL_THEMES"
      :key="id"
      type="button"
      role="radio"
      :aria-checked="modelValue === id"
      class="overflow-hidden border text-left transition"
      :data-hall-theme="id"
      :class="modelValue === id ? 'border-gold ring-1 ring-gold' : 'border-gold/20 hover:border-gold/50'"
      @click="$emit('update:modelValue', id)"
    >
      <span class="block bg-ink-850 p-4">
        <span class="block truncate font-display text-2xl text-parchment">Имя Фамилия</span>
        <span class="block truncate font-elegant italic text-parchment-muted">Соната для скрипки, соч. 1</span>
        <span class="mt-2 flex items-center gap-2">
          <span class="h-3 w-10 bg-gold" />
          <span class="h-3 w-6 bg-gold-dark" />
          <span class="h-3 w-4 bg-parchment-faint" />
        </span>
      </span>
      <span class="block border-t border-gold/20 bg-ink-900 px-4 py-2">
        <span class="block font-caps text-sm font-semibold tracking-[0.12em]" :class="modelValue === id ? 'text-gold-light' : 'text-parchment-muted'">{{ theme.label }}</span>
        <span class="block text-xs text-parchment-faint">{{ theme.about }}</span>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string }>()
defineEmits<{ 'update:modelValue': [value: string] }>()

// The samples are drawn with every era's own faces
useHead({ link: [{ rel: 'stylesheet', href: themeFontsUrl(Object.values(THEME_FONTS).flat()) }] })
</script>
