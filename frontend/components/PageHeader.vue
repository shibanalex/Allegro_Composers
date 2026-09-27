<template>
  <header class="animate-fade-up pb-12 pt-10 text-center sm:pb-16 sm:pt-16">
    <p v-if="eyebrow" class="eyebrow mb-4">{{ eyebrow }}</p>
    <h1 class="text-5xl italic sm:text-7xl">{{ title }}</h1>
    <Ornament class="mx-auto mt-6 w-64" />
    <p v-if="subtitle" class="mx-auto mt-6 max-w-xl font-elegant text-2xl italic text-parchment-muted">{{ subtitle }}</p>
  </header>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  eyebrow: String,
  subtitle: String,
})
</script>
