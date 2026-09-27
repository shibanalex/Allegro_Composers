<template>
  <button
    type="button"
    class="play-btn"
    :class="sizeClass"
    :disabled="opus.audio_type === 'none'"
    :title="opus.audio_type === 'none' ? 'Записи пока нет' : current && player.playing ? 'Пауза' : 'Слушать'"
    @click.prevent.stop="player.toggle(opus)"
  >
    <PlayIcon :playing="current && player.playing" :loading="current && player.loading" />
  </button>
</template>

<script setup lang="ts">
import { usePlayer } from '~/stores/player'
import type { Opus, OpusBrief } from '~/utils/types'

const props = withDefaults(defineProps<{ opus: Opus | OpusBrief; size?: 'sm' | 'md' | 'lg' }>(), { size: 'md' })
const player = usePlayer()
const current = computed(() => player.isCurrent(props.opus.slug))
const sizeClass = computed(() => ({ sm: 'h-9 w-9', md: 'h-12 w-12', lg: 'h-16 w-16' })[props.size])
</script>
