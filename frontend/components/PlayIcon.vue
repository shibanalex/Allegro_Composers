<template>
  <svg v-if="loading && playing" class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M12 3a9 9 0 1 1-9 9" />
  </svg>
  <svg v-else-if="playing" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" /></svg>
  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="ml-0.5"><path d="M6 4l14 8-14 8z" /></svg>
</template>

<script setup lang="ts">
defineProps<{ playing: boolean; loading?: boolean }>()
</script>
