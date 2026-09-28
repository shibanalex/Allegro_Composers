<template>
  <!-- An uploaded picture: its light preview in cards and lists, the original when `full`.
       Pictures uploaded before previews existed fall back to the original. -->
  <img ref="el" :src="current" :alt="alt ?? ''" decoding="async" @error="fallback">
</template>

<script setup lang="ts">
const props = defineProps<{ src: string; alt?: string; full?: boolean }>()

const failed = ref(false)
const current = computed(() => (props.full || failed.value ? props.src : previewOf(props.src)))
watch(() => props.src, () => (failed.value = false))

function fallback() {
  if (current.value !== props.src) failed.value = true
}

// An error during server rendering and hydration fires before the handler is attached
const el = ref<HTMLImageElement>()
onMounted(() => {
  if (el.value?.complete && el.value.naturalWidth === 0) fallback()
})
</script>
