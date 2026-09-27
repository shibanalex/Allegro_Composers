<template>
  <div>
    <p class="field-label">{{ title }}</p>
    <div class="flex flex-wrap gap-2">
      <button
        v-for="f in facets"
        :key="f.value"
        type="button"
        class="chip"
        :class="{ active: active === f.value, 'opacity-40': !f.count && active !== f.value }"
        @click="$emit('pick', active === f.value ? undefined : f.value)"
      >
        {{ f.label }}<span class="ml-1.5 font-display text-xs font-normal italic text-parchment-faint">{{ f.count }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Facet } from '~/utils/types'

defineProps<{ title: string; facets?: Facet[]; active?: string }>()
defineEmits<{ pick: [value: string | undefined] }>()
</script>
