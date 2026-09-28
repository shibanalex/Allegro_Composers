<template>
  <!-- One performance: what is played, by whom, and the recording (an uploaded file or a YouTube video) -->
  <article class="card !p-5 sm:!p-6">
    <header class="flex flex-wrap items-start gap-4">
      <div class="min-w-0 flex-1">
        <p class="eyebrow text-xs">Исполнение<span v-if="performance.recorded_year"> · {{ performance.recorded_year }}</span></p>
        <h3 class="mt-1 text-2xl italic">{{ performance.title }}</h3>
        <p class="mt-1 text-parchment-muted">
          <template v-if="performance.opus">
            <NuxtLink :to="`/opus/${performance.opus.slug}`" class="link">{{ performance.opus.title }}</NuxtLink>
            <span class="text-parchment-faint"> · {{ performance.opus.author.display_name }}</span>
          </template>
          <template v-else-if="performance.composer_name">{{ performance.composer_name }}</template>
        </p>
      </div>
      <NuxtLink v-if="showPerformer" :to="`/@${performance.performer.username}`" class="flex items-center gap-2 text-parchment transition hover:text-gold-light">
        <UserAvatar :user="performance.performer" :size="32" />
        <span class="font-display italic">{{ performance.performer.display_name }}</span>
      </NuxtLink>
    </header>

    <div class="mt-4">
      <audio v-if="performance.audio_type === 'hosted_file' && performance.audio_url" :src="performance.audio_url" controls preload="none" class="w-full" @play="countPlay" />
      <!-- YouTube: a still picture until the listener presses play, then the player (no tracking before that) -->
      <div v-else-if="performance.audio_type === 'youtube'" class="frame frame-thin">
        <div class="frame-inner relative aspect-video bg-ink-950">
          <iframe
            v-if="playing"
            :src="`https://www.youtube-nocookie.com/embed/${performance.audio_source}?autoplay=1`"
            class="absolute inset-0 h-full w-full"
            allow="autoplay; encrypted-media; picture-in-picture"
            allowfullscreen
            :title="performance.title"
          />
          <button v-else type="button" class="group absolute inset-0" :aria-label="`Слушать: ${performance.title}`" @click="startVideo">
            <img :src="`https://i.ytimg.com/vi/${performance.audio_source}/hqdefault.jpg`" alt="" class="h-full w-full object-cover opacity-70 transition group-hover:opacity-90" loading="lazy">
            <span class="absolute left-1/2 top-1/2 flex h-16 w-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-gold/60 bg-ink-950/80 text-2xl text-gold-light transition group-hover:scale-105">▶</span>
          </button>
        </div>
      </div>
    </div>

    <MarkdownContent v-if="performance.description_md" :text="performance.description_md" variant="compact" class="mt-4" />

    <footer v-if="isOwner" class="mt-4 flex items-center gap-4 text-sm text-parchment-faint">
      <span v-if="performance.status !== 'published'" class="chip active">{{ STATUSES[performance.status] }}</span>
      <button type="button" class="ml-auto transition hover:text-gold-light" @click="$emit('edit', performance)">Изменить</button>
      <button type="button" class="transition hover:text-red-300" @click="$emit('remove', performance)">Удалить</button>
    </footer>
  </article>
</template>

<script setup lang="ts">
import type { Performance } from '~/utils/types'

const props = withDefaults(defineProps<{ performance: Performance; showPerformer?: boolean; isOwner?: boolean }>(), {
  showPerformer: true,
  isOwner: false,
})
defineEmits<{ edit: [p: Performance]; remove: [p: Performance] }>()

const api = useApi()
const playing = ref(false)
let counted = false

function countPlay() {
  if (counted) return
  counted = true
  api(`/api/performances/${props.performance.id}/play`, { method: 'POST' }).catch(() => {})
}

function startVideo() {
  playing.value = true
  countPlay()
}
</script>
