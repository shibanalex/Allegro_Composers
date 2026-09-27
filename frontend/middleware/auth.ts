/** Pages that need a logged-in user: definePageMeta({ middleware: 'auth' }) */
export default defineNuxtRouteMiddleware((to) => {
  const { user } = useAuth()
  if (!user.value) return navigateTo(`/login?next=${encodeURIComponent(to.fullPath)}`)
})
