<script setup lang="ts">
// The main page's feed shows new works (each composer's full catalogue is in their hall); old links keep working
const route = useRoute()
await navigateTo({ path: '/', query: { feed: 'works' } }, { redirectCode: 301, replace: true })
</script>

<template>
  <div />
</template>
