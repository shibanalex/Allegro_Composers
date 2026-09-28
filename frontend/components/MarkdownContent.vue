<template>
  <!-- Rendered markdown; timecodes like 02:15 become buttons that emit `seek` -->
  <div class="[overflow-wrap:anywhere]" :class="variant === 'compact' ? 'prose-compact' : 'prose-academia'" @click="onClick" v-html="html" />
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{ text?: string | null; timecodes?: boolean; variant?: 'full' | 'compact' }>(), {
  text: '',
  timecodes: false,
  variant: 'full',
})
const emit = defineEmits<{ seek: [seconds: number] }>()

const html = computed(() => renderMarkdown(props.text || '', { timecodes: props.timecodes }))

const onClick = (e: MouseEvent) => {
  const button = (e.target as HTMLElement).closest<HTMLElement>('.timecode')
  if (button?.dataset.t) emit('seek', Number(button.dataset.t))
}
</script>
