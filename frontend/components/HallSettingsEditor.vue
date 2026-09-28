<template>
  <!-- How the hall looks beyond its era: banner, epigraph, accent metal, which sections and in what order -->
  <div class="space-y-8">
    <div>
      <p class="field-label">Баннер за шапкой зала</p>
      <div v-if="modelValue.cover_url" class="frame frame-thin relative">
        <div class="frame-inner aspect-[4/1]"><MediaImg :src="modelValue.cover_url" alt="" class="h-full w-full object-cover" /></div>
        <button type="button" class="btn-ghost absolute right-1 top-1 z-10 bg-ink-950/70 px-2 text-sm" @click="set({ cover_url: null })">✕</button>
      </div>
      <FileDropzone v-else label="Загрузить баннер" hint="широкая картина: пейзаж, рукопись, зал" accept="image/*" purpose="image" @uploaded="(f) => set({ cover_url: f[0].url })" @error="(m) => $emit('error', m)" />
    </div>

    <div class="grid gap-5 sm:grid-cols-[minmax(0,1fr)_14rem]">
      <div>
        <label class="field-label" for="h-epi">Эпиграф</label>
        <input id="h-epi" :value="modelValue.epigraph || ''" class="field font-elegant text-lg italic" maxlength="300" placeholder="Музыка — это организация времени" @input="set({ epigraph: ($event.target as HTMLInputElement).value || null })">
      </div>
      <div>
        <label class="field-label" for="h-epi-src">Автор эпиграфа</label>
        <input id="h-epi-src" :value="modelValue.epigraph_source || ''" class="field" maxlength="120" placeholder="Стравинский" @input="set({ epigraph_source: ($event.target as HTMLInputElement).value || null })">
      </div>
    </div>

    <div>
      <p class="field-label">Металл отделки</p>
      <div class="flex flex-wrap gap-3">
        <button
          v-for="a in ACCENTS"
          :key="a.id"
          type="button"
          class="flex items-center gap-2 border px-3 py-1.5 transition"
          :class="(modelValue.accent || 'gold') === a.id ? 'border-gold text-parchment' : 'border-gold/20 text-parchment-muted hover:border-gold/50'"
          :aria-pressed="(modelValue.accent || 'gold') === a.id"
          @click="set({ accent: a.id === 'gold' ? null : a.id })"
        >
          <span class="h-4 w-4 rounded-full" :style="{ background: a.swatch }" />{{ a.label }}
        </button>
      </div>
      <p class="mt-2 text-sm text-parchment-faint">«Как в стиле» — золото вашей эпохи; остальные меняют цвет рамок, кнопок и заголовков только в вашем зале.</p>
    </div>

    <div>
      <p class="field-label">Разделы зала и их порядок</p>
      <ul class="divide-y divide-gold/10 border border-gold/15">
        <li v-for="(t, i) in ordered" :key="t" class="flex items-center gap-3 px-3 py-2">
          <input :id="`tab-${t}`" type="checkbox" class="accent-[rgb(var(--c-gold))]" :checked="visible.includes(t)" @change="toggle(t)">
          <label :for="`tab-${t}`" class="flex-1 font-elegant text-lg" :class="visible.includes(t) ? 'text-parchment' : 'text-parchment-faint line-through'">{{ TAB_LABELS[t] }}</label>
          <button type="button" class="btn-ghost px-2" :disabled="i === 0" aria-label="Выше" @click="move(i, -1)">↑</button>
          <button type="button" class="btn-ghost px-2" :disabled="i === ordered.length - 1" aria-label="Ниже" @click="move(i, 1)">↓</button>
        </li>
      </ul>
      <button v-if="modelValue.tabs" type="button" class="link mt-2 text-sm" @click="set({ tabs: null })">Как положено по роли</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HallAccent, HallSettings, HallTab } from '~/utils/types'

const props = defineProps<{ modelValue: HallSettings; role: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: HallSettings]; error: [message: string] }>()

const ACCENTS: { id: HallAccent; label: string; swatch: string }[] = [
  { id: 'gold', label: 'Как в стиле', swatch: 'linear-gradient(135deg, #f3dca6, #c9a36a, #9c7a45)' },
  { id: 'silver', label: 'Серебро', swatch: 'linear-gradient(135deg, #eef0f4, #aeb6c4, #7a8290)' },
  { id: 'copper', label: 'Медь', swatch: 'linear-gradient(135deg, #f6d0b6, #c47c52, #925432)' },
  { id: 'crimson', label: 'Кармин', swatch: 'linear-gradient(135deg, #f6c4c4, #c64e4e, #922c30)' },
  { id: 'emerald', label: 'Изумруд', swatch: 'linear-gradient(135deg, #cceed6, #5eae7c, #3a7c56)' },
  { id: 'sapphire', label: 'Сапфир', swatch: 'linear-gradient(135deg, #c8daf8, #6286ce, #3e5a9c)' },
]
const TAB_LABELS: Record<HallTab, string> = {
  exhibition: 'Выставка', library: 'Библиотека', articles: 'Статьи', performances: 'Исполнения',
  blog: 'Блог', materials: 'Материалы', about: 'О себе',
}
// The sections a role has by default (pages/@[username].vue)
const ROLE_TABS: Record<string, HallTab[]> = {
  composer: ['exhibition', 'library', 'articles', 'blog', 'materials', 'about'],
  theorist: ['articles', 'blog', 'materials', 'about'],
  performer: ['performances', 'blog', 'materials', 'about'],
  listener: ['blog', 'materials', 'about'],
}

const set = (patch: Partial<HallSettings>) => emit('update:modelValue', { ...props.modelValue, ...patch })

const available = computed(() => ROLE_TABS[props.role] || ROLE_TABS.listener)
const visible = computed<HallTab[]>(() => (props.modelValue.tabs?.length ? props.modelValue.tabs : available.value).filter((t) => available.value.includes(t)))
// Visible sections first, in their order, then the hidden ones
const ordered = computed<HallTab[]>(() => [...visible.value, ...available.value.filter((t) => !visible.value.includes(t))])

function toggle(t: HallTab) {
  const next = visible.value.includes(t) ? visible.value.filter((x) => x !== t) : [...visible.value, t]
  if (!next.length) return emit('error', 'Оставьте хотя бы один раздел')
  set({ tabs: ordered.value.filter((x) => next.includes(x)) })
}

function move(i: number, step: number) {
  const list = [...ordered.value]
  ;[list[i], list[i + step]] = [list[i + step], list[i]]
  set({ tabs: list.filter((x) => visible.value.includes(x)) })
}
</script>
