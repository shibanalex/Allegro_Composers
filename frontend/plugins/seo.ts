// Tags every page shares: its one canonical address, the site name for link previews, search engine verification codes
export default defineNuxtPlugin(() => {
  const route = useRoute()
  const origin = useSiteOrigin()
  const { yandexVerification, googleVerification } = useRuntimeConfig().public
  const canonical = computed(() => `${origin}${route.path === '/' ? '/' : route.path.replace(/\/+$/, '')}`)

  useHead({
    link: [{ rel: 'canonical', href: canonical }],
    meta: [
      { property: 'og:url', content: canonical },
      { property: 'og:site_name', content: 'Allegro' },
      { property: 'og:locale', content: 'ru_RU' },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' },
      ...(yandexVerification ? [{ name: 'yandex-verification', content: String(yandexVerification) }] : []),
      ...(googleVerification ? [{ name: 'google-site-verification', content: String(googleVerification) }] : []),
    ],
  })
})
