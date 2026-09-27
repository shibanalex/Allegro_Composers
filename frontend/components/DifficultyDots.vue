<template>
  <span class="inline-flex items-center gap-1" :title="`Сложность: ${DIFFICULTY[value]}`">
    <span v-for="i in 5" :key="i" class="h-1.5 w-1.5 rotate-45" :class="i <= value ? 'bg-gold' : 'bg-gold/20'" />
  </span>
</template>

<script setup lang="ts">
defineProps<{ value: number }>()
</script>
