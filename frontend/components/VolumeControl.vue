<template>
  <div class="flex w-32 items-center gap-2 text-parchment-muted">
    <button type="button" class="transition hover:text-gold" :aria-label="player.volume ? 'Выключить звук' : 'Включить звук'" @click="toggleMute">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
        <path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor" />
        <path v-if="player.volume > 0" d="M16 9a4 4 0 0 1 0 6" />
        <path v-if="player.volume > 0.5" d="M18.5 6.5a8 8 0 0 1 0 11" />
        <path v-if="player.volume === 0" d="M16 9l5 6M21 9l-5 6" />
      </svg>
    </button>
    <input
      type="range"
      class="range"
      min="0"
      max="1"
      step="0.01"
      :value="player.volume"
      :style="{ '--fill': `${player.volume * 100}%` }"
      aria-label="Громкость"
      @input="player.setVolume(Number(($event.target as HTMLInputElement).value))"
    >
  </div>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'

const player = usePlayer()
let previous = 0.85
const toggleMute = () => {
  if (player.volume) {
    previous = player.volume
    player.setVolume(0)
  } else {
    player.setVolume(previous || 0.85)
  }
}
</script>
