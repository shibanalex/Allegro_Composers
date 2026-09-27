<template>
  <footer class="mt-24 border-t border-gold/10 bg-ink-950/60">
    <div class="container-page flex flex-col items-center gap-4 py-10 text-center">
      <span class="title-script text-6xl">Allegro</span>
      <Ornament class="w-56" />
      <p class="font-elegant text-xl italic text-parchment-muted">Сообщество композиторов, исполнителей и теоретиков</p>
      <nav class="flex flex-wrap items-center justify-center gap-6 font-caps text-sm font-semibold tracking-[0.2em] text-parchment-faint">
        <NuxtLink to="/" class="transition hover:text-gold">Главная</NuxtLink>
        <NuxtLink to="/library" class="transition hover:text-gold">Библиотека</NuxtLink>
        <span>© {{ year }} Allegro</span>
      </nav>
    </div>
  </footer>
</template>

<script setup lang="ts">
const year = new Date().getFullYear()
</script>
