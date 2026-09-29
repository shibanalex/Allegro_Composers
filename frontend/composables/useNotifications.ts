/**
 * The bell's number of unread notifications: asked for once a minute and whenever the tab comes back
 * into view. One small indexed query; no open connection is kept.
 */
export function useNotifications() {
  const unread = useState<number>('notifications-unread', () => 0)
  const api = useApi()

  async function refresh() {
    try {
      unread.value = (await api<{ count: number }>('/api/notifications/unread')).count
    } catch {}
  }

  return { unread, refresh }
}

/** Push in this browser: the service worker, the permission, the subscription sent to the site */
export function usePush() {
  const api = useApi()
  const supported = computed(() => import.meta.client && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window)

  const decode = (key: string) => {
    const b64 = (key + '='.repeat((4 - (key.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
    return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
  }

  async function current(): Promise<PushSubscription | null> {
    if (!supported.value) return null
    const reg = await navigator.serviceWorker.getRegistration('/sw.js')
    return reg ? reg.pushManager.getSubscription() : null
  }

  /** Ask the browser's permission and subscribe; returns false when the member said no */
  async function enable(publicKey: string): Promise<boolean> {
    if (!supported.value) return false
    if ((await Notification.requestPermission()) !== 'granted') return false
    const reg = await navigator.serviceWorker.register('/sw.js')
    await navigator.serviceWorker.ready
    const sub = (await reg.pushManager.getSubscription())
      || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: decode(publicKey) })
    const json = sub.toJSON()
    await api('/api/notifications/push', { method: 'POST', body: { endpoint: json.endpoint, keys: json.keys } })
    return true
  }

  async function disable() {
    const sub = await current()
    if (!sub) return
    await api('/api/notifications/push/remove', { method: 'POST', body: { endpoint: sub.endpoint } }).catch(() => {})
    await sub.unsubscribe()
  }

  return { supported, current, enable, disable }
}
