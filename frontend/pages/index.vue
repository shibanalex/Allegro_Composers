<template>
  <div>
    <!-- Salon hero -->
    <section class="relative mt-6 flex flex-col items-center px-6 pb-14 pt-16 text-center sm:mt-10">
      <div class="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[26rem] w-[26rem] max-w-full -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(201,163,106,0.14),transparent_65%)] blur-2xl" />
      <CornerFlourish class="absolute left-0 top-0 w-14 sm:w-20" />
      <CornerFlourish class="absolute right-0 top-0 w-14 -scale-x-100 sm:w-20" />
      <CornerFlourish class="absolute bottom-0 left-0 w-14 -scale-y-100 sm:w-20" />
      <CornerFlourish class="absolute bottom-0 right-0 w-14 -scale-100 sm:w-20" />

      <p class="eyebrow animate-fade-up">Сообщество композиторов</p>
      <h1 class="title-script animate-fade-up text-[6rem] sm:text-[8.5rem]" style="animation-delay: .1s">Allegro</h1>
      <Ornament class="-mt-4 w-64 animate-fade-up" style="animation-delay: .2s" />
      <p class="mt-6 max-w-2xl animate-fade-up font-elegant text-2xl italic text-parchment-muted" style="animation-delay: .3s">
        Опусы, партитуры и разборы — звук, ноты и теоретическая беседа в одном окне.
      </p>
      <div class="mt-8 flex animate-fade-up flex-wrap justify-center gap-4" style="animation-delay: .4s">
        <template v-if="user">
          <NuxtLink to="/create/opus" class="btn-primary">+ Опубликовать опус</NuxtLink>
          <NuxtLink :to="`/@${user.username}`" class="btn-secondary">Мой зал</NuxtLink>
        </template>
        <template v-else>
          <NuxtLink v-if="registrationOpen" to="/register" class="btn-primary">Открыть свой зал</NuxtLink>
          <NuxtLink to="/library" class="btn-secondary">В библиотеку</NuxtLink>
        </template>
      </div>
    </section>

    <!-- The composers' halls: where a visitor finds their works, blogs and materials -->
    <section v-if="composers.length" class="mb-16 mt-6">
      <p class="eyebrow mb-6 text-center">Залы композиторов</p>
      <div class="mx-auto grid max-w-5xl gap-5" :class="composers.length > 1 ? 'sm:grid-cols-2 lg:grid-cols-3' : 'max-w-md'">
        <ComposerCard v-for="c in composers" :key="c.id" :composer="c" />
      </div>
    </section>

    <PageTabs :tabs="tabs">
      <!-- Все опусы -->
      <template #opuses>
        <EmptyState v-if="!opuses.length">{{ user || registrationOpen ? 'Опусов пока нет — станьте первым' : 'Скоро здесь появятся первые опусы' }}</EmptyState>
        <div class="grid gap-x-10 gap-y-14 sm:grid-cols-2 lg:grid-cols-3">
          <OpusCard v-for="o in opuses" :key="o.id" :opus="o" />
        </div>
        <div v-if="opuses.length < (opusPage?.total || 0)" class="mt-14 text-center">
          <button class="btn-secondary" :disabled="loadingMore" @click="loadMore">Показать ещё</button>
        </div>
      </template>

      <!-- Теория и статьи -->
      <template #articles>
        <EmptyState v-if="!articles.length">Статей пока нет</EmptyState>
        <div v-else class="space-y-14">
          <PostCard :post="articles[0]" featured />
          <div v-if="articles.length > 1" class="grid gap-x-10 gap-y-14 md:grid-cols-2">
            <PostCard v-for="p in articles.slice(1)" :key="p.id" :post="p" />
          </div>
        </div>
      </template>

      <!-- Мастерская / Рецензии -->
      <template #workshop>
        <div class="mb-8 flex flex-wrap items-center justify-between gap-4">
          <p class="max-w-xl font-elegant text-xl italic text-parchment-muted">
            Здесь авторы просят разбора: выкладывают запись и ноты, а коллеги отвечают с таймкодами и примерами.
          </p>
          <NuxtLink v-if="user || registrationOpen" :to="user ? '/create/post?kind=workshop' : '/login?next=/create/post%3Fkind%3Dworkshop'" class="btn-secondary">+ Тема в мастерскую</NuxtLink>
        </div>
        <EmptyState v-if="!workshop.length">В мастерской пока тихо</EmptyState>
        <div class="space-y-5">
          <WorkshopCard v-for="p in workshop" :key="p.id" :post="p" />
        </div>
      </template>
    </PageTabs>
  </div>
</template>

<script setup lang="ts">
import type { Opus, Page, Post, Profile } from '~/utils/types'

useSeoMeta({
  title: 'Allegro — сообщество композиторов',
  description: 'Сообщество композиторов: опусы с партитурами и записями, блоги и материалы авторов.',
})

const api = useApi()
const { user, registrationOpen } = useAuth()

const { data } = await useAsyncData('salon', async () => {
  const [opuses, articles, workshop, composers] = await Promise.all([
    api<Page<Opus>>('/api/opuses', { params: { limit: 12 } }),
    api<Page<Post>>('/api/posts', { params: { kind: 'article', limit: 12 } }),
    api<Page<Post>>('/api/posts', { params: { kind: 'workshop', limit: 20 } }),
    api<Profile[]>('/api/users').catch(() => [] as Profile[]), // decoration: never takes the page down
  ])
  return { opuses, articles, workshop, composers }
})

const opusPage = computed(() => data.value?.opuses)
const extra = ref<Opus[]>([])
const opuses = computed(() => [...(data.value?.opuses.items || []), ...extra.value])
const articles = computed(() => data.value?.articles.items || [])
const workshop = computed(() => data.value?.workshop.items || [])
const composers = computed(() => data.value?.composers || [])

// Members see every section (to post there); a visitor only the ones with something inside
const tabs = computed(() => {
  const all = [
    { id: 'opuses', label: 'Все опусы', count: data.value?.opuses.total },
    { id: 'articles', label: 'Теория и статьи', count: data.value?.articles.total },
    { id: 'workshop', label: 'Мастерская', count: data.value?.workshop.total },
  ]
  const filled = all.filter((t) => t.count)
  return user.value || !filled.length ? all : filled
})

const loadingMore = ref(false)
async function loadMore() {
  loadingMore.value = true
  try {
    const page = await api<Page<Opus>>('/api/opuses', { params: { limit: 12, offset: opuses.value.length } })
    extra.value.push(...page.items)
  } finally {
    loadingMore.value = false
  }
}
</script>
