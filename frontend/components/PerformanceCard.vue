<template>
  <!-- One performance: whose work is played, by whom, and the recording (an uploaded file or a YouTube video).
       The work always stays its composer's: the performer is named as the one who plays it. -->
  <article :class="bare ? '' : 'card !p-5 sm:!p-6'">
    <header>
      <p class="eyebrow text-xs">Исполнение<span v-if="performance.recorded_year"> · запись {{ performance.recorded_year }} г.</span></p>
      <h3 class="mt-1 text-2xl">
        <NuxtLink v-if="performance.opus" :to="`/opus/${performance.opus.slug}`" class="transition hover:text-gold-light">«{{ performance.opus.title }}»</NuxtLink>
        <template v-else>«{{ performance.title }}»</template>
      </h3>
      <p class="mt-1 text-parchment-muted">
        <template v-if="performance.opus">
          сочинение <NuxtLink :to="`/@${performance.opus.author.username}`" class="link">{{ performance.opus.author.display_name }}</NuxtLink>
        </template>
        <template v-else-if="performance.composer_name">композитор {{ performance.composer_name }}</template>
        <template v-if="showPerformer && !bare">
          · исполняет <NuxtLink :to="`/@${performance.performer.username}`" class="link">{{ performance.performer.display_name }}</NuxtLink>
        </template>
      </p>
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

const props = withDefaults(defineProps<{ performance: Performance; showPerformer?: boolean; isOwner?: boolean; bare?: boolean }>(), {
  showPerformer: true,
  isOwner: false,
  bare: false, // inside a feed entry, which already names the performer
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
