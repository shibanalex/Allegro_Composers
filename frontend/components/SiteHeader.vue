<template>
  <header class="sticky top-0 z-40 border-b border-gold/10 bg-ink-950/80 backdrop-blur-md">
    <div class="container-page flex h-16 items-center gap-2 sm:h-20 sm:gap-4 lg:gap-8" :class="{ 'xl:max-w-[90rem]': route.meta.wide }">
      <NuxtLink to="/" class="group flex shrink-0 items-center gap-1" @click="menuOpen = false">
        <span class="hidden font-display text-2xl text-gold/80 transition group-hover:text-gold-light sm:inline">𝄞</span>
        <span class="title-script brand -ml-2 text-4xl sm:ml-0 sm:text-5xl">Allegro</span>
      </NuxtLink>

      <nav class="hidden items-center gap-8 md:flex">
        <NuxtLink v-for="item in links" :key="item.to" :to="item.to" class="nav-link" :class="{ active: isActive(item.to) }">
          {{ item.label }}
        </NuxtLink>
      </nav>

      <div class="ml-auto flex min-w-0 items-center gap-1.5 sm:gap-3">
        <ThemeSwitch />
        <!-- Quick search (Ctrl+K / ⌘K) -->
        <button
          type="button"
          class="flex items-center gap-3 border border-gold/20 bg-ink-950/60 px-2.5 py-1.5 text-parchment-faint transition hover:border-gold/50 hover:text-parchment"
          aria-label="Поиск"
          @click="search.open = true"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
          <span class="hidden font-elegant italic lg:inline">Поиск</span>
          <kbd class="hidden font-mono text-xs text-parchment-faint/80 lg:inline">{{ shortcut }}</kbd>
        </button>

        <template v-if="user">
          <!-- + Создать -->
          <div ref="createRoot" class="relative">
            <button type="button" class="btn-primary px-4 py-1.5 text-sm" :aria-expanded="createOpen" @click="createOpen = !createOpen">
              <span class="text-lg leading-none">+</span><span class="hidden sm:inline">Создать</span>
            </button>
            <Transition name="drop">
              <div v-if="createOpen" class="absolute right-0 top-full mt-2 w-64 border border-gold/25 bg-ink-900/95 py-2 shadow-2xl shadow-black backdrop-blur" @click="createOpen = false">
                <!-- What the member's role lets them publish -->
                <NuxtLink v-if="can('publish_opus')" to="/create/opus" class="menu-item"><span class="menu-icon">♪</span>Сочинение<small>в библиотеку</small></NuxtLink>
                <NuxtLink v-if="can('publish_performance')" :to="`/@${user.username}?tab=performances`" class="menu-item"><span class="menu-icon">♫</span>Исполнение<small>запись, видео</small></NuxtLink>
                <NuxtLink v-if="can('publish_article')" to="/create/post?kind=article" class="menu-item"><span class="menu-icon">¶</span>Статью<small>теория, обзор, эссе</small></NuxtLink>
                <NuxtLink :to="`/@${user.username}?tab=blog`" class="menu-item"><span class="menu-icon">✎</span>Запись в блог<small>как в канале</small></NuxtLink>
                <NuxtLink :to="`/@${user.username}?tab=materials`" class="menu-item"><span class="menu-icon">⎗</span>Материал<small>книга, ссылка, файл</small></NuxtLink>
                <NuxtLink v-if="can('publish_news')" to="/create/post?kind=news" class="menu-item"><span class="menu-icon">✦</span>Новость<small>для всех</small></NuxtLink>
              </div>
            </Transition>
          </div>

          <!-- Profile -->
          <div ref="profileRoot" class="relative">
            <button type="button" class="block rounded-full transition hover:ring-2 hover:ring-gold/60" :aria-expanded="profileOpen" aria-label="Профиль" @click="profileOpen = !profileOpen">
              <UserAvatar :user="user" :size="38" />
            </button>
            <Transition name="drop">
              <div v-if="profileOpen" class="absolute right-0 top-full mt-2 w-56 border border-gold/25 bg-ink-900/95 py-2 shadow-2xl shadow-black backdrop-blur" @click="profileOpen = false">
                <p class="truncate px-4 pb-2 pt-1 font-display italic text-parchment">{{ user.display_name }}</p>
                <NuxtLink :to="`/@${user.username}`" class="menu-item">Мой зал</NuxtLink>
                <NuxtLink to="/settings" class="menu-item">Оформить зал</NuxtLink>
                <NuxtLink v-if="can('manage_site') || can('invite')" to="/admin" class="menu-item">Управление</NuxtLink>
                <button type="button" class="menu-item w-full text-left" @click="logout">Выйти</button>
              </div>
            </Transition>
          </div>
        </template>
        <NuxtLink v-else :to="`/login?next=${encodeURIComponent(route.fullPath)}`" class="btn-secondary px-3 py-1.5 text-sm sm:px-4">Войти</NuxtLink>

        <button class="p-1.5 text-parchment-muted hover:text-gold md:hidden" :aria-expanded="menuOpen" aria-label="Меню" @click="menuOpen = !menuOpen">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path v-if="!menuOpen" d="M4 7h16M4 12h16M4 17h16" />
            <path v-else d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>
    </div>

    <nav v-if="menuOpen" class="border-t border-gold/10 bg-ink-950/95 md:hidden">
      <NuxtLink v-for="item in links" :key="item.to" :to="item.to" class="nav-link block px-4 py-4" :class="{ active: isActive(item.to) }" @click="menuOpen = false">
        {{ item.label }}
      </NuxtLink>
    </nav>
  </header>
</template>

<script setup lang="ts">
const route = useRoute()
const { user, can, logout: doLogout } = useAuth()
const search = useSearchPalette()

// The main page (works, performances, articles, blogs) and your own hall
const links = computed(() => [
  { to: '/', label: 'Главная' },
  ...(user.value ? [{ to: `/@${user.value.username}`, label: 'Мой зал' }] : []),
])
const isActive = (to: string) => (to === '/' ? route.path === '/' : route.path.startsWith(to))

const menuOpen = ref(false)
const createOpen = ref(false)
const profileOpen = ref(false)
const createRoot = ref<HTMLElement>()
const profileRoot = ref<HTMLElement>()
const shortcut = ref('Ctrl K')

const logout = async () => {
  await doLogout()
  navigateTo('/')
}

// Close dropdowns on outside click / navigation
const onDocClick = (e: MouseEvent) => {
  if (createRoot.value && !createRoot.value.contains(e.target as Node)) createOpen.value = false
  if (profileRoot.value && !profileRoot.value.contains(e.target as Node)) profileOpen.value = false
}
watch(() => route.fullPath, () => {
  menuOpen.value = createOpen.value = profileOpen.value = false
})
onMounted(() => {
  document.addEventListener('click', onDocClick)
  if (/Mac|iPhone|iPad/.test(navigator.platform)) shortcut.value = '⌘K'
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.nav-link {
  @apply font-caps text-lg font-semibold text-parchment-muted transition hover:text-gold-light;
  letter-spacing: 0.22em;
}
.nav-link.active {
  @apply text-gold;
}
.menu-item {
  @apply flex items-baseline gap-3 px-4 py-2 font-elegant text-lg text-parchment transition hover:bg-gold/10 hover:text-gold-light;
}
.menu-item small {
  @apply ml-auto font-serif text-xs italic text-parchment-faint;
}
.menu-icon {
  @apply w-4 text-center font-display text-gold;
}
.drop-enter-active, .drop-leave-active { transition: opacity .2s, transform .2s; }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
