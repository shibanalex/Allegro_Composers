<template>
  <footer class="mt-24 border-t border-gold/10 bg-ink-950/60">
    <div class="container-page flex flex-col items-center gap-4 py-10 text-center">
      <span class="title-script brand text-6xl">Allegro</span>
      <Ornament class="w-56" />
      <p class="font-elegant text-xl italic text-parchment-muted">Сообщество композиторов, теоретиков, исполнителей и слушателей</p>
      <nav class="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 font-caps text-sm font-semibold tracking-[0.2em] text-parchment-faint">
        <NuxtLink v-for="l in LINKS" :key="l.to" :to="l.to" class="transition hover:text-gold">{{ l.label }}</NuxtLink>
      </nav>
      <p class="font-caps text-xs tracking-[0.2em] text-parchment-faint/70">© {{ year }} Allegro</p>
      <p class="max-w-md text-xs leading-relaxed text-parchment-faint/60">
        Для статистики посещений сайт использует
        <a href="https://yandex.ru/legal/metrica_termsofuse/" target="_blank" rel="noopener" class="underline decoration-gold/30 underline-offset-2 hover:text-gold-light">Яндекс Метрику</a>:
        она собирает обезличенные данные о визитах и использует cookie.
      </p>
    </div>
  </footer>
</template>

<script setup lang="ts">
const year = new Date().getFullYear()
// Sections of the «О сообществе» page
const LINKS = [
  { to: '/about', label: 'О нас' },
  { to: '/about?tab=links', label: 'Ссылки' },
  { to: '/about?tab=news', label: 'Новости' },
  { to: '/about?tab=feedback', label: 'Предложения' },
]
</script>
