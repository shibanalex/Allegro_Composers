export const formatDate = (value?: string | null) =>
  value ? new Date(value).toLocaleDateString('ru-RU', { year: 'numeric', month: 'long', day: 'numeric' }) : ''

export const formatSize = (bytes?: number | null) => {
  if (bytes == null) return ''
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}

/** 84.3 → "01:24" (or "1:02:05" for long works) */
export const formatTime = (seconds?: number | null) => {
  if (seconds == null || !isFinite(seconds)) return '--:--'
  const s = Math.max(0, Math.floor(seconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = String(s % 60).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${sec}` : `${String(m).padStart(2, '0')}:${sec}`
}

/** "1:24" / "01:24" / "84" → 84; null if not a time */
export const parseTime = (text: string): number | null => {
  const value = text.trim()
  if (/^\d+(\.\d+)?$/.test(value)) return Number(value)
  const parts = value.split(':').map(Number)
  if (parts.length < 2 || parts.length > 3 || parts.some((p) => !Number.isFinite(p))) return null
  return parts.reduce((acc, p) => acc * 60 + p, 0)
}

export const plural = (n: number, one: string, few: string, many: string) => {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
  return many
}

/** Only web, mail and same-site links; anything else (javascript:, data:, //other.site) becomes inert */
const SAFE_URL = /^(https?:\/\/|mailto:|\/(?![\/\\]))/i
export const safeUrl = (url?: string | null) => (url && SAFE_URL.test(url.trim()) ? url.trim() : undefined)

/** A redirect target inside the site (login ?next=...): "/path", never "//host" or "/\host" */
export const safeNext = (value: unknown, fallback = '/') =>
  typeof value === 'string' && /^\/(?![\/\\])/.test(value) ? value : fallback

export const isImage = (a?: { content_type?: string }) => !!a?.content_type?.startsWith('image/')

export const fileExtension = (name = '') => (name.includes('.') ? name.split('.').pop()!.toUpperCase() : 'FILE')

export const initials = (name = '') =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
