<template>
  <!-- «Выставка»: the composer's works, sorted and grouped the way the visitor wants -->
  <div>
    <!-- Sorting and grouping only make sense once there is something to arrange -->
    <div v-if="opuses.length > 3" class="mb-10 flex flex-wrap items-end gap-x-8 gap-y-4 border-b border-gold/15 pb-6">
      <div>
        <p class="field-label">Группировать</p>
        <div class="flex flex-wrap gap-2">
          <button v-for="g in GROUPS" :key="g.id" type="button" class="chip" :class="{ active: group === g.id }" @click="group = g.id">{{ g.label }}</button>
        </div>
      </div>
      <div>
        <p class="field-label">Порядок</p>
        <div class="flex flex-wrap gap-2">
          <button v-for="s in SORTS" :key="s.id" type="button" class="chip" :class="{ active: sort === s.id }" @click="sort = s.id">{{ s.label }}</button>
        </div>
      </div>
      <div class="ml-auto flex gap-2">
        <button type="button" class="chip px-2.5" :class="{ active: view === 'grid' }" title="Витрина" aria-label="Витрина" @click="view = 'grid'">▦</button>
        <button type="button" class="chip px-2.5" :class="{ active: view === 'list' }" title="Список" aria-label="Список" @click="view = 'list'">☰</button>
      </div>
    </div>

    <div v-if="isOwner" class="mb-10 flex flex-wrap justify-end gap-3">
      <NuxtLink to="/create/collection" class="btn-secondary px-4 py-1.5 text-sm">+ Цикл</NuxtLink>
      <NuxtLink to="/create/opus" class="btn-primary px-4 py-1.5 text-sm">+ Произведение</NuxtLink>
    </div>

    <EmptyState v-if="!opuses.length">{{ isOwner ? 'Выставка ждёт первого произведения' : 'Произведений пока нет' }}</EmptyState>

    <div class="space-y-16">
      <section v-for="g in groups" :key="g.key">
        <header v-if="g.title" class="mb-8 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-gold/15 pb-3">
          <h3 class="text-3xl italic">{{ g.title }}</h3>
          <span class="font-display text-lg italic text-parchment-faint">{{ g.items.length }}</span>
          <p v-if="g.note" class="w-full font-elegant text-lg italic text-parchment-muted">{{ g.note }}</p>
          <NuxtLink v-if="isOwner && g.editId" :to="`/create/collection?edit=${g.editId}`" class="link ml-auto font-caps text-sm font-semibold tracking-[0.15em]">Изменить цикл</NuxtLink>
        </header>

        <div v-if="view === 'grid'" class="grid gap-x-10 gap-y-14 sm:grid-cols-2 lg:grid-cols-3">
          <OpusCard v-for="o in g.items" :key="o.id" :opus="o" :show-author="false" />
        </div>
        <ol v-else class="divide-y divide-gold/10">
          <OpusRow v-for="(o, i) in g.items" :key="o.id" :opus="o" :number="g.numbered ? roman(i + 1) + '.' : undefined" />
        </ol>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Collection, Opus } from '~/utils/types'

const props = defineProps<{ opuses: Opus[]; collections: Collection[]; isOwner: boolean }>()

const GROUPS = [
  { id: 'none', label: 'Все вместе' },
  { id: 'cycle', label: 'По циклам' },
  { id: 'genre', label: 'По жанру' },
  { id: 'year', label: 'По годам' },
] as const
const SORTS = [
  { id: 'new', label: 'Новые' },
  { id: 'old', label: 'Ранние' },
  { id: 'title', label: 'По названию' },
  { id: 'popular', label: 'Популярные' },
] as const
type GroupId = (typeof GROUPS)[number]['id']
type SortId = (typeof SORTS)[number]['id']

// Remember the visitor's choice for this browser
const saved = (key: string, fallback: string) => {
  try {
    return localStorage.getItem(key) || fallback
  } catch {
    return fallback
  }
}
const group = ref<GroupId>('none')
const sort = ref<SortId>('new')
const view = ref<'grid' | 'list'>('grid')
onMounted(() => {
  const g = saved('hall-group', 'none')
  group.value = GROUPS.some((x) => x.id === g) ? (g as GroupId) : 'none'  // an old choice may no longer exist
  sort.value = saved('hall-sort', 'new') as SortId
  view.value = saved('hall-view', 'grid') as 'grid' | 'list'
})
watch([group, sort, view], ([g, s, v]) => {
  try {
    localStorage.setItem('hall-group', g)
    localStorage.setItem('hall-sort', s)
    localStorage.setItem('hall-view', v)
  } catch {}
})

/** Year of composition, or of publication if the author didn't give one */
const yearOf = (o: Opus) => o.year ?? new Date(o.created_at).getFullYear()

const sorted = computed(() => {
  const items = [...props.opuses]
  const by = {
    new: (a: Opus, b: Opus) => yearOf(b) - yearOf(a) || b.created_at.localeCompare(a.created_at),
    old: (a: Opus, b: Opus) => yearOf(a) - yearOf(b) || a.created_at.localeCompare(b.created_at),
    title: (a: Opus, b: Opus) => a.title.localeCompare(b.title, 'ru'),
    popular: (a: Opus, b: Opus) => b.play_count - a.play_count,
  }[sort.value]
  return items.sort(by)
})

interface Group { key: string; title?: string; note?: string | null; items: Opus[]; editId?: string; numbered?: boolean }

const byKey = (keyOf: (o: Opus) => string, labels: Record<string, string>) => {
  const order = Object.keys(labels)
  const map = new Map<string, Opus[]>()
  for (const o of sorted.value) map.set(keyOf(o), [...(map.get(keyOf(o)) || []), o])
  return [...map.entries()]
    .sort(([a], [b]) => order.indexOf(a) - order.indexOf(b))
    .map(([key, items]): Group => ({ key, title: labels[key] || key, items }))
}

const groups = computed<Group[]>(() => {
  if (group.value === 'genre') return byKey((o) => o.genre, Object.fromEntries(Object.entries(GENRES).map(([k, g]) => [k, g.label])))
  if (group.value === 'year') {
    const years = [...new Set(sorted.value.map(yearOf))].sort((a, b) => b - a)
    return years.map((y) => ({ key: String(y), title: String(y), items: sorted.value.filter((o) => yearOf(o) === y) }))
  }
  if (group.value === 'cycle') {
    // Cycles keep the order the composer gave them; everything else follows the chosen sort
    const inCycles = new Set(props.collections.flatMap((c) => c.opuses.map((o) => o.id)))
    const visible = new Map(props.opuses.map((o) => [o.id, o]))
    const cycles: Group[] = props.collections
      .map((c) => ({
        key: c.id,
        title: c.year ? `${c.title} (${c.year})` : c.title,
        note: c.description,
        items: c.opuses.map((o) => visible.get(o.id) || o),
        editId: c.id,
        numbered: true,
      }))
      .filter((g) => g.items.length)
    const rest = sorted.value.filter((o) => !inCycles.has(o.id))
    return rest.length ? [...cycles, { key: 'rest', title: 'Отдельные произведения', items: rest }] : cycles
  }
  return [{ key: 'all', items: sorted.value }]
})

const roman = (n: number) => ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV'][n - 1] || String(n)
</script>
