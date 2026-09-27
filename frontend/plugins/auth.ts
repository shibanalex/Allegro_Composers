// Resolve the logged-in user before the first navigation, so route middleware already knows it.
// On the server this runs once per request; the state is handed over to the browser.
export default defineNuxtPlugin(async () => {
  await callOnce('auth', () => useAuth().fetchMe())
})
