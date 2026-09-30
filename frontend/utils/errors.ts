/**
 * A page that couldn't load its main thing: «not found» only when the server said so (404). Anything else —
 * the free hosting waking up, a deploy restarting the server, a timeout — is a temporary failure, and the
 * visitor is asked to reload instead of being told the page doesn't exist.
 */
export function pageError(error: any, notFound: string) {
  const status = error?.statusCode ?? error?.status ?? error?.response?.status
  if (status === 404) return createError({ statusCode: 404, statusMessage: notFound, fatal: true })
  return createError({
    statusCode: 503,
    statusMessage: 'Сервер не ответил вовремя — такое бывает, пока он просыпается. Обновите страницу через несколько секунд.',
    fatal: true,
  })
}
