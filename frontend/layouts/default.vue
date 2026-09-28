<template>
  <div class="flex min-h-screen flex-col" :class="{ 'pb-20': player.track }">
    <div class="canvas-bg" aria-hidden="true" />
    <SiteHeader />
    <!-- Pages with side columns (the main feed) ask for more room: definePageMeta({ wide: true }) -->
    <main class="container-page flex-1" :class="{ 'xl:max-w-[90rem]': route.meta.wide }">
      <slot />
    </main>
    <SiteFooter />
    <ClientOnly>
      <PlayerBar />
      <SearchPalette />
    </ClientOnly>
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'

const player = usePlayer()
const route = useRoute()
</script>
