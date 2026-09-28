/** Pages for administrators only: definePageMeta({ middleware: 'admin' }) */
export default defineNuxtRouteMiddleware((to) => {
  const { user } = useAuth()
  if (!user.value) return navigateTo(`/login?next=${encodeURIComponent(to.fullPath)}`)
  if (!user.value.is_admin) return navigateTo('/')
})
