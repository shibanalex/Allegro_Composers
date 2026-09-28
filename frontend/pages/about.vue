<template>
  <!-- About the community: who we are, links, news and members' suggestions -->
  <div>
    <PageHeader eyebrow="Allegro" title="О сообществе" />

    <PageTabs :tabs="tabs">
      <template #about>
        <SitePageEditor slug="about" />
      </template>

      <template #links>
        <SitePageEditor slug="links" empty-text="Ссылок пока нет" placeholder="- [YouTube](https://…)&#10;- [Telegram](https://t.me/…)" />
      </template>

      <template #news>
        <div class="mx-auto max-w-3xl">
          <div v-if="can('publish_news')" class="mb-8 flex justify-end">
            <NuxtLink to="/create/post?kind=news" class="btn-primary px-4 py-1.5 text-sm">+ Новость</NuxtLink>
          </div>
          <EmptyState v-if="!news.length">Новостей пока нет</EmptyState>
          <div class="space-y-10">
            <PostCard v-for="p in news" :key="p.id" :post="p" />
          </div>
        </div>
      </template>

      <template #feedback>
        <FeedbackBoard />
      </template>
    </PageTabs>
  </div>
</template>

<script setup lang="ts">
import type { Page, Post } from '~/utils/types'

useSeoMeta({
  title: 'О сообществе — Allegro',
  description: 'Allegro — сообщество композиторов, теоретиков, исполнителей и слушателей. Новости, ссылки и предложения участников.',
})

const api = useApi()
const { can } = useAuth()
const { data } = await useAsyncData('news', () => api<Page<Post>>('/api/posts', { params: { kind: 'news', limit: 20 } }))
const news = computed(() => data.value?.items || [])

const tabs = [
  { id: 'about', label: 'О нас' },
  { id: 'links', label: 'Ссылки' },
  { id: 'news', label: 'Новости' },
  { id: 'feedback', label: 'Предложения' },
]
</script>
