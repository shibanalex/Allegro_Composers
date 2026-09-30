<template>
  <!-- «Поделиться»: the phone's own share sheet (messengers, mail…), or the link copied on a computer -->
  <button type="button" class="inline-flex items-center gap-1.5 transition hover:text-gold-light" :title="`Поделиться: ${absolute}`" @click.stop="share">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
      <path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" />
    </svg>
    <span :class="{ 'max-sm:sr-only': !copied }">{{ copied ? 'Скопировано' : 'Поделиться' }}</span>
  </button>
</template>

<script setup lang="ts">
const props = defineProps<{ path: string; title?: string }>()

const copied = ref(false)
const absolute = computed(() => (import.meta.client ? new URL(props.path, location.origin).href : props.path))

async function share() {
  const url = absolute.value
  // On phones: the system sheet; a visitor who closes it has simply changed their mind
  if (navigator.share && matchMedia('(pointer: coarse)').matches) {
    try {
      await navigator.share({ title: props.title || 'Allegro', url })
      return
    } catch (e: any) {
      if (e?.name === 'AbortError') return
    }
  }
  try {
    await navigator.clipboard.writeText(url)
  } catch {
    prompt('Скопируйте ссылку:', url) // old browsers and insecure contexts: the link at least can be copied by hand
    return
  }
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}
</script>
