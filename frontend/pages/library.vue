<script setup lang="ts">
// The catalogue of all works moved to the main page («Сочинения»); old links keep working
const route = useRoute()
await navigateTo({ path: '/', query: { ...route.query, tab: 'works' } }, { redirectCode: 301, replace: true })
</script>

<template>
  <div />
</template>
