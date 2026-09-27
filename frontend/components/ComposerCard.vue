<template>
  <!-- A composer's hall on the main page: portrait, name and what is inside -->
  <NuxtLink :to="`/@${composer.username}`" class="card group flex items-center gap-5 !p-5 transition hover:border-gold/40">
    <div class="portrait h-24 w-20 shrink-0">
      <img v-if="composer.avatar_url" :src="composer.avatar_url" :alt="composer.display_name">
      <div v-else class="flex items-center justify-center bg-ink-700 font-display text-3xl italic text-gold/50">{{ initials(composer.display_name) }}</div>
    </div>
    <div class="min-w-0">
      <p class="truncate font-display text-2xl italic transition group-hover:text-gold-light">{{ composer.display_name }}</p>
      <p v-if="composer.pseudonym" class="title-script -ml-1 -mt-1 truncate !p-0 text-3xl">{{ composer.pseudonym }}</p>
      <p v-if="summary" class="mt-1 font-caps text-sm font-semibold tracking-[0.15em] text-parchment-faint">{{ summary }}</p>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
import type { Profile } from '~/utils/types'

const props = defineProps<{ composer: Profile }>()

const summary = computed(() => {
  const s = props.composer.stats
  if (!s) return ''
  return [
    s.opuses && `${s.opuses} ${plural(s.opuses, 'опус', 'опуса', 'опусов')}`,
    s.posts && `${s.posts} ${plural(s.posts, 'запись', 'записи', 'записей')} в блоге`,
  ].filter(Boolean).join(' · ')
})
</script>
