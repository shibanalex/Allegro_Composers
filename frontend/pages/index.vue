<template>
  <div>
    <!-- Hero -->
    <section class="relative mt-6 flex flex-col items-center px-6 pb-14 pt-16 text-center sm:mt-10">
      <div class="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[26rem] w-[26rem] max-w-full -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(201,163,106,0.14),transparent_65%)] blur-2xl" />
      <CornerFlourish class="absolute left-0 top-0 w-14 sm:w-20" />
      <CornerFlourish class="absolute right-0 top-0 w-14 -scale-x-100 sm:w-20" />
      <CornerFlourish class="absolute bottom-0 left-0 w-14 -scale-y-100 sm:w-20" />
      <CornerFlourish class="absolute bottom-0 right-0 w-14 -scale-100 sm:w-20" />

      <p class="eyebrow animate-fade-up">Сообщество композиторов</p>
      <h1 class="title-script animate-fade-up text-[6rem] sm:text-[8.5rem]" style="animation-delay: .1s">Allegro</h1>
      <Ornament class="-mt-4 w-64 animate-fade-up" style="animation-delay: .2s" />
      <div v-if="user" class="mt-8 flex animate-fade-up flex-wrap justify-center gap-4" style="animation-delay: .3s">
        <NuxtLink :to="`/@${user.username}`" class="btn-secondary">Мой зал</NuxtLink>
      </div>
    </section>

    <!-- Members' halls: where a visitor finds their works, performances, articles and blogs -->
    <section v-if="members.length" class="mb-16 mt-6">
      <p class="eyebrow mb-6 text-center">Залы участников</p>
      <div class="mx-auto grid max-w-5xl gap-5" :class="members.length > 1 ? 'sm:grid-cols-2 lg:grid-cols-3' : 'max-w-md'">
        <ComposerCard v-for="m in members" :key="m.id" :composer="m" />
      </div>
    </section>

    <PageTabs :tabs="tabs">
      <!-- Сочинения: the catalogue of every composer's works -->
      <template #works>
        <OpusCatalog />
      </template>

      <!-- Исполнения -->
      <template #performances>
        <PerformanceList empty-text="Исполнений пока нет" />
      </template>

      <!-- Статьи и обзоры -->
      <template #articles>
        <div v-if="can('publish_article')" class="mb-8 flex justify-end">
          <NuxtLink to="/create/post?kind=article" class="btn-secondary px-4 py-1.5 text-sm">+ Статья</NuxtLink>
        </div>
        <EmptyState v-if="!articles.length">Статей пока нет</EmptyState>
        <div v-else class="space-y-14">
          <PostCard :post="articles[0]" featured />
          <div v-if="articles.length > 1" class="grid gap-x-10 gap-y-14 md:grid-cols-2">
            <PostCard v-for="p in articles.slice(1)" :key="p.id" :post="p" />
          </div>
        </div>
      </template>

      <!-- Блоги: every member's posts in one feed (later — recommendations) -->
      <template #blogs>
        <HallChannel feed :is-owner="false" :initial="data?.blogs || { items: [], total: 0 }" />
      </template>
    </PageTabs>
  </div>
</template>

<script setup lang="ts">
import type { Page, Post, Profile } from '~/utils/types'

useSeoMeta({
  title: 'Allegro — сообщество композиторов',
  description: 'Сообщество композиторов, теоретиков и исполнителей: сочинения с партитурами и записями, исполнения, статьи и блоги.',
})

const api = useApi()
const { user, can } = useAuth()

const { data } = await useAsyncData('home', async () => {
  const [articles, blogs, members, works, performances] = await Promise.all([
    api<Page<Post>>('/api/posts', { params: { kind: 'article', limit: 12 } }),
    api<Page<Post>>('/api/posts', { params: { kind: 'note', limit: 20 } }),
    api<Profile[]>('/api/users').catch(() => [] as Profile[]), // decoration: never takes the page down
    api<Page<unknown>>('/api/opuses', { params: { limit: 1 } }),
    api<Page<unknown>>('/api/performances', { params: { limit: 1 } }),
  ])
  return { articles, blogs, members, worksTotal: works.total, performancesTotal: performances.total }
})

const articles = computed(() => data.value?.articles.items || [])
const members = computed(() => data.value?.members || [])

// Members see every section (to post there); a visitor only the ones with something inside
const tabs = computed(() => {
  const all = [
    { id: 'works', label: 'Сочинения', count: data.value?.worksTotal },
    { id: 'performances', label: 'Исполнения', count: data.value?.performancesTotal },
    { id: 'articles', label: 'Статьи и обзоры', count: data.value?.articles.total },
    { id: 'blogs', label: 'Блоги', count: data.value?.blogs.total },
  ]
  const filled = all.filter((t) => t.count)
  return user.value || !filled.length ? all : filled
})
</script>
