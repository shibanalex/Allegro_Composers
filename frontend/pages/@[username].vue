<template>
  <!-- A member's hall in the style of their era (data-hall-theme on <html>): portrait, name, manifesto, sections by role -->
  <div v-if="profile" class="hall">
    <header class="hall-header relative mt-8 grid items-center gap-10 px-2 py-12 sm:mt-12 md:grid-cols-[auto_minmax(0,1fr)] md:gap-14 md:px-10">
      <CornerFlourish class="hall-flourish absolute left-0 top-0 w-14 sm:w-20" />
      <CornerFlourish class="hall-flourish absolute right-0 top-0 w-14 -scale-x-100 sm:w-20" />
      <CornerFlourish class="hall-flourish absolute bottom-0 left-0 w-14 -scale-y-100 sm:w-20" />
      <CornerFlourish class="hall-flourish absolute bottom-0 right-0 w-14 -scale-100 sm:w-20" />

      <div class="portrait mx-auto h-64 w-52 sm:h-72 sm:w-56">
        <img v-if="profile.avatar_url" :src="profile.avatar_url" :alt="profile.display_name">
        <div v-else class="flex items-center justify-center bg-ink-700 font-display text-6xl italic text-gold/50">{{ initials(profile.display_name) }}</div>
      </div>

      <div class="text-center md:text-left">
        <p class="eyebrow">{{ role.label }} · @{{ profile.username }}</p>
        <h1 class="hall-name mt-3 text-5xl italic sm:text-6xl">{{ profile.display_name }}</h1>
        <p v-if="profile.pseudonym" class="title-script -ml-2 text-5xl sm:text-6xl">{{ profile.pseudonym }}</p>
        <p v-if="profile.bio" class="mt-4 max-w-2xl font-elegant text-2xl italic leading-snug text-parchment-muted">{{ profile.bio }}</p>

        <div class="mt-6 flex flex-wrap items-center justify-center gap-3 md:justify-start">
          <a v-for="l in profile.links" :key="l.url" :href="safeUrl(l.url)" target="_blank" rel="noopener nofollow" class="chip">{{ l.label }} ↗</a>
          <NuxtLink v-if="isOwner" to="/settings" class="btn-secondary px-4 py-1.5 text-sm">Оформить зал</NuxtLink>
        </div>
      </div>
    </header>

    <PageTabs :tabs="tabs" class="mt-12">
      <template #exhibition>
        <HallExhibition :opuses="showcase" :collections="collections" :is-owner="isOwner" />
        <p v-if="isOwner && opuses.length && !featuredCount" class="mt-8 text-center text-sm text-parchment-faint">
          Сейчас на выставке все сочинения. Чтобы выбрать избранные, отметьте их ★ в «Библиотеке».
        </p>
      </template>

      <template #library>
        <OpusCatalog :author="username" :is-owner="isOwner" @featured="onFeatured" />
      </template>

      <template #articles>
        <div v-if="isOwner && can('publish_article')" class="mb-8 flex justify-end">
          <NuxtLink to="/create/post?kind=article" class="btn-primary px-4 py-1.5 text-sm">+ Статья</NuxtLink>
        </div>
        <EmptyState v-if="!articles.length">{{ isOwner ? 'Первая статья — за вами' : 'Статей пока нет' }}</EmptyState>
        <div class="grid gap-x-10 gap-y-14 md:grid-cols-2">
          <PostCard v-for="p in articles" :key="p.id" :post="p" />
        </div>
      </template>

      <template #performances>
        <PerformanceList :performer="username" :empty-text="isOwner ? 'Добавьте первое исполнение' : 'Исполнений пока нет'" />
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
const { user, can } = useAuth()
const username = String(route.params.username).toLowerCase()

const { data: profile, error } = await useAsyncData(`profile-${username}`, () => api<Profile>(`/api/users/${username}`))
if (error.value || !profile.value) throw createError({ statusCode: 404, statusMessage: 'Автор не найден', fatal: true })

const isOwner = computed(() => user.value?.username === username)
const role = computed(() => ROLES[profile.value?.role || 'listener'] || ROLES.listener)

// The owner also sees drafts and unlisted works in their own hall
const { data } = await useAsyncData(`hall-${username}`, async () => {
  const mine = isOwner.value ? { mine: true } : {}
  const [opuses, posts, articles, collections, materials] = await Promise.all([
    api<Page<Opus>>('/api/opuses', { params: { author: username, limit: 100, ...mine } }),
    api<Page<Post>>('/api/posts', { params: { author: username, kind: 'note', limit: 20, ...mine } }),
    api<Page<Post>>('/api/posts', { params: { author: username, kind: 'article', limit: 50, ...mine } }),
    api<Collection[]>('/api/collections', { params: { author: username } }),
    api<Material[]>('/api/materials', { params: { author: username } }),
  ])
  return { opuses, posts, articles, collections, materials }
})

const opuses = computed(() => data.value?.opuses.items || [])
const featuredCount = computed(() => opuses.value.filter((o) => o.featured).length)
// «Выставка»: the works the composer picked; until they pick any, all of them
const showcase = computed(() => (featuredCount.value ? opuses.value.filter((o) => o.featured) : opuses.value))
const articles = computed(() => data.value?.articles.items || [])
const collections = computed(() => data.value?.collections || [])
const materials = computed(() => data.value?.materials || [])

function onFeatured(saved: Opus) {
  const opus = opuses.value.find((o) => o.id === saved.id)
  if (opus) opus.featured = saved.featured
}

// Sections of a hall by role; a section outside the role still shows when it has content
const ROLE_TABS: Record<string, string[]> = {
  composer: ['exhibition', 'library', 'articles', 'blog', 'materials', 'about'],
  theorist: ['articles', 'blog', 'materials', 'about'],
  performer: ['performances', 'blog', 'materials', 'about'],
  listener: ['blog', 'materials', 'about'],
}
const tabs = computed(() => {
  const stats = profile.value?.stats || {}
  const all = [
    { id: 'exhibition', label: 'Выставка', count: showcase.value.length },
    { id: 'library', label: 'Библиотека', count: opuses.value.length },
    { id: 'articles', label: 'Статьи', count: data.value?.articles.total ?? 0 },
    { id: 'performances', label: 'Исполнения', count: stats.performances ?? 0 },
    { id: 'blog', label: 'Блог', count: data.value?.posts.total ?? 0 },
    { id: 'materials', label: 'Материалы', count: materials.value.length },
    { id: 'about', label: 'О себе', count: null, empty: !profile.value?.about_md },
  ]
  const own = ROLE_TABS[profile.value?.role || 'listener'] || ROLE_TABS.listener
  const hasContent = (t: (typeof all)[number]) => !(t.empty ?? t.count === 0)
  // The owner sees their role's sections (to fill them in); a visitor only the ones with something inside
  const shown = all.filter((t) => hasContent(t) || (isOwner.value && own.includes(t.id)))
  return shown.length ? shown : all.filter((t) => t.id === 'about')
})

// The whole page takes the hall's era — header, footer and canvas too — and loads that era's faces
useHead({
  htmlAttrs: { 'data-hall-theme': computed(() => profile.value?.hall_theme || 'romantic') },
  link: computed(() => {
    const families = THEME_FONTS[profile.value?.hall_theme || '']
    return families ? [{ rel: 'stylesheet', href: themeFontsUrl(families) }] : []
  }),
})

useSeoMeta({
  title: () => `${profile.value?.display_name}${profile.value?.pseudonym ? ` (${profile.value.pseudonym})` : ''} — ${role.value.label.toLowerCase()} · Allegro`,
  description: () => profile.value?.bio || `${role.value.label}: ${profile.value?.display_name} на Allegro — сочинения, исполнения, статьи и блог.`,
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
      jobTitle: role.value.label,
      url: `${origin}/@${username}`,
      sameAs: profile.value?.links.map((l) => l.url).filter((u) => u.startsWith('http')),
    },
  }))],
})
</script>
