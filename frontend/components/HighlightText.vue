<template>
  <!-- The text with the searched words marked; built from pieces, never as HTML -->
  <span><template v-for="(part, i) in parts" :key="i"><mark v-if="part.hit" class="bg-gold/25 text-gold-light">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template></span>
</template>

<script setup lang="ts">
const props = defineProps<{ text: string; words: string[] }>()

const parts = computed(() => {
  const text = props.text || ''
  // Same folding as the server: case and «ё» don't matter (the length of the text doesn't change)
  const folded = text.toLowerCase().replace(/ё/g, 'е')
  const hits: [number, number][] = []
  for (const w of props.words.filter(Boolean)) {
    let from = 0
    let at: number
    while ((at = folded.indexOf(w, from)) >= 0) {
      // extend to the end of the word, so the whole «полифонии» is marked, not just «полифон»
      let end = at + w.length
      while (end < text.length && /[\p{L}\p{N}]/u.test(text[end])) end++
      hits.push([at, end])
      from = end
    }
  }
  hits.sort((a, b) => a[0] - b[0])
  const out: { text: string; hit: boolean }[] = []
  let pos = 0
  for (const [start, end] of hits) {
    if (start < pos) continue
    if (start > pos) out.push({ text: text.slice(pos, start), hit: false })
    out.push({ text: text.slice(start, end), hit: true })
    pos = end
  }
  if (pos < text.length) out.push({ text: text.slice(pos), hit: false })
  return out
})
</script>
