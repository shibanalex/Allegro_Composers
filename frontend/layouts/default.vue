<template>
  <div class="flex min-h-screen flex-col" :class="{ 'pb-20': player.track }">
    <div class="canvas-bg" aria-hidden="true" />
    <SiteHeader />
    <main class="container-page flex-1">
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
</script>
