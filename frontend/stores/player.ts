import { defineStore } from 'pinia'
import type { Marker, Opus, OpusBrief } from '~/utils/types'

/** What the player needs to know about a piece */
export interface Track {
  slug: string
  title: string
  subtitle?: string | null
  author: { username: string; display_name: string }
  audio_type: Opus['audio_type']
  audio_source?: string | null
  audio_url?: string | null
  duration?: number | null
  cover_url?: string | null
  markers: Marker[]
}

/** Implemented by <PlayerBar>, which owns the <audio> element / YouTube iframe */
export interface PlayerController {
  load(track: Track, startAt: number, autoplay: boolean): void
  play(): void
  pause(): void
  seek(seconds: number): void
  setVolume(volume: number): void
}

let controller: PlayerController | null = null

export const toTrack = (opus: Opus | OpusBrief): Track => ({
  slug: opus.slug,
  title: opus.title,
  subtitle: opus.subtitle,
  author: opus.author,
  audio_type: opus.audio_type,
  audio_source: opus.audio_source,
  audio_url: opus.audio_url,
  duration: opus.audio_duration_seconds,
  cover_url: 'cover_url' in opus ? opus.cover_url : null,
  markers: 'markers' in opus ? opus.markers : [],
})

export const usePlayer = defineStore('player', {
  state: () => ({
    track: null as Track | null,
    playing: false,
    loading: false,
    time: 0,
    duration: 0,
    volume: 0.85,
    stopAt: null as number | null, // playing a stretch: pause when the recording reaches this second
  }),
  getters: {
    isCurrent: (state) => (slug?: string) => !!slug && state.track?.slug === slug,
    progress: (state) => (state.duration ? state.time / state.duration : 0),
  },
  actions: {
    register(ctrl: PlayerController | null) {
      controller = ctrl
    },
    /** Start (or resume) a piece; `at` jumps to a second of the recording */
    play(opus: Opus | OpusBrief | Track, at?: number) {
      if (opus.audio_type === 'none') return
      const track = 'markers' in opus && 'duration' in opus ? (opus as Track) : toTrack(opus as Opus)
      if (this.track?.slug !== track.slug) {
        this.track = track
        this.time = at ?? 0
        this.duration = track.duration || 0
        this.loading = true
        controller?.load(track, at ?? 0, true)
        // Fire-and-forget play counter
        $fetch(`/api/opuses/${track.slug}/play`, { method: 'POST' }).catch(() => {})
      } else {
        if (at != null) this.seek(at)
        controller?.play()
      }
    },
    /** Play a stretch of a piece: from `start`, pausing at `end` */
    playRange(opus: Opus | OpusBrief | Track, start: number, end: number) {
      this.play(opus, start)
      this.stopAt = end
    },
    /** Called as the recording plays (by <PlayerBar>): ends a stretch on time */
    tick(time: number) {
      this.time = time
      if (this.stopAt != null && time >= this.stopAt) {
        this.stopAt = null
        controller?.pause()
      }
    },
    pause() {
      controller?.pause()
    },
    toggle(opus?: Opus | OpusBrief) {
      if (opus && !this.isCurrent(opus.slug)) return this.play(opus)
      this.playing ? this.pause() : controller?.play()
    },
    seek(seconds: number) {
      this.stopAt = null // moving elsewhere ends a stretch
      this.time = Math.max(0, seconds)
      controller?.seek(this.time)
    },
    setVolume(volume: number) {
      this.volume = Math.min(1, Math.max(0, volume))
      controller?.setVolume(this.volume)
    },
    close() {
      controller?.pause()
      this.track = null
      this.playing = false
    },
  },
})

/** Score page that should be visible at `time` given page-turn markers */
export function pageAt(markers: Marker[], time: number): number | null {
  let page: number | null = null
  for (const m of markers) {
    if (m.timestamp_seconds <= time + 0.05) page = m.page_number
  }
  return page
}
