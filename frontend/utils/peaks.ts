/** The waveform of an uploaded recording, drawn once by the server (backend core.peaks) */
export interface Peaks { duration: number; peaks: number[] }

// One request per recording for the whole visit: the feed may show the same sketch twice
const cache = new Map<string, Promise<Peaks | null>>()

export function loadPeaks(url: string | null | undefined): Promise<Peaks | null> {
  if (!url) return Promise.resolve(null)
  if (!cache.has(url)) {
    const request = $fetch<Peaks>('/api/media/peaks', { params: { url } })
      .then((p) => (p?.peaks?.length ? p : null))
      .catch(() => {
        cache.delete(url) // not ready yet (just uploaded): ask again next time
        return null
      })
    cache.set(url, request)
  }
  return cache.get(url)!
}

/** The site's gold in canvas colours, read from the theme (each era of a hall has its own) */
export function themeColour(name: string, alpha = 1): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(`--c-${name}`).trim()
  const [r, g, b] = value.split(/\s+/).map(Number)
  return Number.isFinite(b) ? `rgba(${r}, ${g}, ${b}, ${alpha})` : `rgba(201, 163, 106, ${alpha})`
}
