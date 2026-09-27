<template>
  <div class="mb-10 flex flex-wrap items-end justify-between gap-4 border-b border-gold/15 pb-5">
    <div>
      <p class="eyebrow">{{ eyebrow }}</p>
      <h2 class="mt-2 text-4xl italic sm:text-5xl">{{ title }}</h2>
    </div>
    <router-link v-if="link" :to="link" class="font-caps text-base font-semibold tracking-[0.2em] text-parchment-muted transition hover:text-gold">
      {{ linkLabel }} →
    </router-link>
  </div>
</template>

<script setup>
defineProps({
  eyebrow: String,
  title: { type: String, required: true },
  link: String,
  linkLabel: String,
})
</script>
