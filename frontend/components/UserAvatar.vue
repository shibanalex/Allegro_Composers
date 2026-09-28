<template>
  <span
    class="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-ink-700 font-display text-gold-light ring-1 ring-gold/40"
    :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${size * 0.4}px` }"
  >
    <MediaImg v-if="user.avatar_url" :src="user.avatar_url" :alt="user.display_name" class="h-full w-full object-cover" />
    <span v-else>{{ initials(user.display_name) }}</span>
  </span>
</template>

<script setup lang="ts">
import type { UserBrief } from '~/utils/types'

withDefaults(defineProps<{ user: UserBrief; size?: number }>(), { size: 32 })
</script>
