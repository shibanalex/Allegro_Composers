<template>
  <div v-if="profile">
    <!-- The composer's hall: portrait, name, manifesto -->
    <header class="relative mt-8 grid items-center gap-10 px-2 py-12 sm:mt-12 md:grid-cols-[auto_minmax(0,1fr)] md:gap-14 md:px-10">
      <CornerFlourish class="absolute left-0 top-0 w-14 sm:w-20" />
      <CornerFlourish class="absolute right-0 top-0 w-14 -scale-x-100 sm:w-20" />
      <CornerFlourish class="absolute bottom-0 left-0 w-14 -scale-y-100 sm:w-20" />
      <CornerFlourish class="absolute bottom-0 right-0 w-14 -scale-100 sm:w-20" />

      <div class="portrait mx-auto h-64 w-52 sm:h-72 sm:w-56">
        <img v-if="profile.avatar_url" :src="profile.avatar_url" :alt="profile.display_name">
        <div v-else class="flex items-center justify-center bg-ink-700 font-display text-6xl italic text-gold/50">{{ initials(profile.display_name) }}</div>
      </div>

      <div class="text-center md:text-left">
        <p class="eyebrow">Зал композитора · @{{ profile.username }}</p>
        <h1 class="mt-3 text-5xl italic sm:text-6xl">{{ profile.display_name }}</h1>
        <p v-if="profile.pseudonym" class="title-script -ml-2 text-5xl sm:text-6xl">{{ profile.pseudonym }}</p>
        <p v-if="profile.bio" class="mt-4 max-w-2xl font-elegant text-2xl italic leading-snug text-parchment-muted">{{ profile.bio }}</p>

        <div class="mt-6 flex flex-wrap items-center justify-center gap-3 md:justify-start">
          <a v-for="l in profile.links" :key="l.url" :href="safeUrl(l.url)" target="_blank" rel="noopener nofollow" class="chip">{{ l.label }} ↗</a>
          <template v-if="isOwner">
            <NuxtLink to="/settings" class="btn-secondary px-4 py-1.5 text-sm">Оформить зал</NuxtLink>
          </template>
        </div>
      </div>
    </header>

    <PageTabs :tabs="tabs" class="mt-12">
      <template #exhibition>
        <HallExhibition :opuses="opuses" :collections="collections" :is-owner="isOwner" />
      </template>

      <template #blog>
        <HallChannel :username="username" :is-owner="isOwner" :initial="data?.posts || { items: [], total: 0 }" />
      </template>

      <template #materials>
        <HallMaterials :initial="materials" :is-owner="isOwner" />
      </template>

      <template #about>
        <div class="mx-auto max-w-prose">
          <MarkdownContent v-if="profile.about_md" :text="profile.about_md" />
          <EmptyState v-else>Автор пока ничего не рассказал о себе</EmptyState>
          <p class="mt-10 text-center font-caps text-sm font-semibold tracking-[0.2em] text-parchment-faint">
            На Allegro с {{ formatDate(profile.created_at) }}
          </p>
        </div>
      </template>
    </PageTabs>
  </div>
</template>

<script setup lang="ts">
import type { Collection, Material, Opus, Page, Post, Profile } from '~/utils/types'

const route = useRoute()
const api = useApi()
const { user } = useAuth()
const username = String(route.params.username).toLowerCase()

const { data: profile, error } = await useAsyncData(`profile-${username}`, () => api<Profile>(`/api/users/${username}`))
if (error.value || !profile.value) throw createError({ statusCode: 404, statusMessage: 'Автор не найден', fatal: true })

const isOwner = computed(() => user.value?.username === username)

// The owner also sees drafts and unlisted works in their own hall
const { data } = await useAsyncData(`hall-${username}`, async () => {
  const mine = isOwner.value ? { mine: true } : {}
  const [opuses, posts, collections, materials] = await Promise.all([
    api<Page<Opus>>('/api/opuses', { params: { author: username, limit: 100, ...mine } }),
    api<Page<Post>>('/api/posts', { params: { author: username, kind: ['note', 'article'], limit: 20, ...mine } }),
    api<Collection[]>('/api/collections', { params: { author: username } }),
    api<Material[]>('/api/materials', { params: { author: username } }),
  ])
  return { opuses, posts, collections, materials }
})

const opuses = computed(() => data.value?.opuses.items || [])
const collections = computed(() => data.value?.collections || [])
const materials = computed(() => data.value?.materials || [])

// The owner sees every section (to fill it in); a visitor only the ones with something inside
const tabs = computed(() => {
  const all = [
    { id: 'exhibition', label: 'Выставка', count: opuses.value.length },
    { id: 'blog', label: 'Блог', count: data.value?.posts.total ?? 0 },
    { id: 'materials', label: 'Материалы', count: materials.value.length },
    { id: 'about', label: 'О себе', count: null, empty: !profile.value?.about_md },
  ]
  const filled = all.filter((t) => !(t.empty ?? t.count === 0))
  return isOwner.value || !filled.length ? all : filled
})

useSeoMeta({
  title: () => `${profile.value?.display_name}${profile.value?.pseudonym ? ` (${profile.value.pseudonym})` : ''} — композитор · Allegro`,
  description: () => profile.value?.bio || `Произведения, блог и материалы композитора ${profile.value?.display_name} на Allegro.`,
  ogImage: () => profile.value?.avatar_url || undefined,
  ogType: 'profile',
})

const origin = useSiteOrigin()
useHead({
  script: [computed(() => jsonLd({
    '@context': 'https://schema.org',
    '@type': 'ProfilePage',
    mainEntity: {
      '@type': 'Person',
      name: profile.value?.display_name,
      alternateName: profile.value?.pseudonym || undefined,
      description: profile.value?.bio || undefined,
      image: profile.value?.avatar_url || undefined,
      jobTitle: 'Композитор',
      url: `${origin}/@${username}`,
      sameAs: profile.value?.links.map((l) => l.url).filter((u) => u.startsWith('http')),
    },
  }))],
})
</script>
