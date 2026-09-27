<template>
  <ul class="divide-y divide-gold/10 border-y border-gold/15">
    <li v-for="file in files" :key="file.url" class="flex items-center gap-4 py-3">
      <span class="flex h-11 w-11 shrink-0 items-center justify-center border border-gold/40 bg-ink-950/60 font-caps text-xs font-semibold tracking-wider text-gold">
        {{ fileExtension(file.name) }}
      </span>
      <div class="min-w-0 flex-1">
        <p class="truncate text-parchment">{{ file.name }}</p>
        <p class="text-sm text-parchment-faint">{{ formatSize(file.size) }}</p>
      </div>
      <slot name="action" :file="file">
        <a :href="file.url" :download="file.name" class="btn-ghost">Скачать ↓</a>
      </slot>
    </li>
  </ul>
</template>

<script setup>

defineProps({
  files: { type: Array, required: true },
})
</script>
