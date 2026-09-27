<template>
  <input
    type="range"
    class="range"
    min="0"
    :max="player.duration || 0"
    step="0.1"
    :value="dragging ?? player.time"
    :style="{ '--fill': `${fill}%` }"
    aria-label="Позиция"
    @input="dragging = Number(($event.target as HTMLInputElement).value)"
    @change="commit"
  >
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'

const player = usePlayer()
const dragging = ref<number | null>(null)
const fill = computed(() => (player.duration ? ((dragging.value ?? player.time) / player.duration) * 100 : 0))

const commit = () => {
  if (dragging.value != null) player.seek(dragging.value)
  dragging.value = null
}
</script>
