<template>
  <!-- The bell next to the avatar: how many new publications; opens the notifications page -->
  <NuxtLink
    to="/notifications"
    class="relative flex h-9 w-9 items-center justify-center text-parchment-muted transition hover:text-gold-light"
    :aria-label="unread ? `Уведомления: ${unread} ${plural(unread, 'новое', 'новых', 'новых')}` : 'Уведомления'"
    :title="unread ? `${unread} ${plural(unread, 'новое уведомление', 'новых уведомления', 'новых уведомлений')}` : 'Уведомления'"
  >
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
    <span
      v-if="unread"
      class="absolute -right-0.5 -top-0.5 flex h-[1.15rem] min-w-[1.15rem] items-center justify-center rounded-full bg-gold px-1 font-sans text-[0.68rem] font-bold leading-none text-ink-950"
    >
      {{ unread > 99 ? '99+' : unread }}
    </span>
  </NuxtLink>
</template>

<script setup lang="ts">
const { unread, refresh } = useNotifications()

let timer: ReturnType<typeof setInterval> | undefined
const onVisible = () => document.visibilityState === 'visible' && refresh()
onMounted(() => {
  refresh()
  timer = setInterval(refresh, 60_000)
  document.addEventListener('visibilitychange', onVisible)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisible)
})
</script>
