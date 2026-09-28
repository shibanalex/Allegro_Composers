<template>
  <div>
    <div class="grid grid-cols-2 gap-5 sm:grid-cols-3">
      <button
        v-for="(img, i) in images"
        :key="img.url"
        type="button"
        class="frame frame-thin group aspect-[4/3]"
        :class="images.length === 1 || (images.length === 3 && i === 0) ? 'col-span-2 sm:col-span-3 aspect-[16/9]' : ''"
        @click="current = i"
      >
        <div class="frame-inner">
          <MediaImg
            :src="img.url"
            :alt="img.name"
            loading="lazy"
            class="h-full w-full object-cover opacity-90 transition duration-700 group-hover:scale-105 group-hover:opacity-100"
          />
        </div>
      </button>
    </div>

    <Teleport to="body">
      <div
        v-if="current !== null"
        class="fixed inset-0 z-50 flex flex-col bg-ink-950/95 backdrop-blur-sm"
        @click.self="close"
      >
        <div class="flex items-center justify-between p-4 text-sm text-parchment-muted">
          <span class="truncate">{{ images[current].name }}</span>
          <span class="flex shrink-0 items-center gap-4">
            <span>{{ current + 1 }} / {{ images.length }}</span>
            <button class="btn-ghost" aria-label="Закрыть" @click="close">✕</button>
          </span>
        </div>
        <div class="relative flex min-h-0 flex-1 items-center justify-center px-4 pb-8 sm:px-16" @click.self="close">
          <img :src="images[current].url" :alt="images[current].name" class="max-h-full max-w-full object-contain" style="box-shadow: 0 0 0 5px rgb(var(--c-gold-dark)), 0 0 0 6px #000, 0 40px 80px -20px #000">
          <template v-if="images.length > 1">
            <button class="nav left-2 sm:left-4" aria-label="Предыдущее" @click="step(-1)">‹</button>
            <button class="nav right-2 sm:right-4" aria-label="Следующее" @click="step(1)">›</button>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  images: { type: Array, required: true },
})

const current = ref(null)
const close = () => (current.value = null)
const step = (d) => (current.value = (current.value + d + props.images.length) % props.images.length)

const onKey = (e) => {
  if (current.value === null) return
  if (e.key === 'Escape') close()
  if (e.key === 'ArrowLeft') step(-1)
  if (e.key === 'ArrowRight') step(1)
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.nav {
  @apply absolute top-1/2 -translate-y-1/2 px-3 py-6 font-display text-5xl text-parchment/60 transition hover:text-gold;
}
</style>
