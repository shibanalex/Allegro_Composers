<template>
  <!-- The community chat on its own page (header: «Чат», between «Участники» and «Мой зал») -->
  <div class="mx-auto w-full max-w-3xl pt-2 sm:pt-6">
    <h1 class="sr-only">Чат сообщества Allegro</h1>
    <ChatRoom class="h-[calc(100dvh-6.5rem)] min-h-[24rem] sm:h-[calc(100dvh-9rem)]" :class="{ 'max-h-[calc(100dvh-12rem)]': player.track }" />
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'

const player = usePlayer()

useSeoMeta({
  title: 'Чат — Allegro',
  description: 'Общий чат сообщества Allegro: композиторы, теоретики, исполнители и слушатели',
})
</script>
