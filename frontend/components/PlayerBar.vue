<template>
  <!-- Owns the actual <audio> / YouTube player so music keeps playing across navigation -->
  <div>
    <audio
      ref="audio"
      preload="metadata"
      @timeupdate="onTime"
      @loadedmetadata="onMeta"
      @play="player.playing = true; player.loading = false"
      @pause="player.playing = false"
      @waiting="player.loading = true"
      @playing="player.loading = false"
      @ended="player.playing = false"
    />

    <Transition name="bar">
      <div
        v-show="player.track && !hidden"
        class="fixed inset-x-0 bottom-0 z-40 border-t border-gold/25 bg-ink-950/90 shadow-[0_-20px_40px_-20px_#000] backdrop-blur-md"
      >
        <div class="container-page flex items-center gap-3 py-2.5 sm:gap-5">
          <!-- YouTube must stay visible while playing: a small framed video -->
          <div v-show="player.track?.audio_type === 'youtube'" class="frame frame-thin hidden h-[54px] w-24 shrink-0 sm:block">
            <div class="frame-inner"><div ref="ytHost" class="h-full w-full" /></div>
          </div>
          <MediaImg v-if="player.track?.audio_type !== 'youtube' && player.track?.cover_url" :src="player.track.cover_url" alt="" class="hidden h-12 w-12 shrink-0 object-cover ring-1 ring-gold/40 sm:block" />

          <button class="play-btn h-11 w-11" :aria-label="player.playing ? 'Пауза' : 'Играть'" @click="player.toggle()">
            <PlayIcon :playing="player.playing" :loading="player.loading" />
          </button>

          <div class="min-w-0 flex-1">
            <div class="flex items-baseline gap-3">
              <NuxtLink v-if="player.track" :to="`/opus/${player.track.slug}`" class="truncate font-display italic text-parchment transition hover:text-gold-light">
                {{ player.track.title }}
              </NuxtLink>
              <span class="hidden truncate text-sm text-parchment-faint sm:inline">{{ player.track?.author.display_name }}</span>
              <span class="ml-auto shrink-0 font-mono text-xs text-parchment-muted">{{ formatTime(player.time) }} / {{ formatTime(player.duration) }}</span>
            </div>
            <SeekBar class="mt-1" />
          </div>

          <VolumeControl class="hidden md:flex" />
          <button class="btn-ghost px-2" aria-label="Закрыть плеер" @click="player.close()">✕</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { usePlayer, type PlayerController, type Track } from '~/stores/player'

const player = usePlayer()
const route = useRoute()
const audio = ref<HTMLAudioElement>()
const ytHost = ref<HTMLElement>()

// On the page of the playing opus the sticky transport replaces this bar
const hidden = computed(() => !!player.track && route.path === `/opus/${player.track.slug}`)

const onTime = () => {
  if (player.track?.audio_type === 'hosted_file' && audio.value) player.time = audio.value.currentTime
}
const onMeta = () => {
  if (audio.value && isFinite(audio.value.duration)) player.duration = audio.value.duration
}

// ---------------------------------------------------------------- YouTube IFrame API
let yt: any = null
let ytReady: Promise<any> | null = null
let ytTimer: ReturnType<typeof setInterval> | undefined

function loadYouTubeApi(): Promise<any> {
  if (ytReady) return ytReady
  ytReady = new Promise((resolve) => {
    const w = window as any
    if (w.YT?.Player) return resolve(w.YT)
    w.onYouTubeIframeAPIReady = () => resolve(w.YT)
    const script = document.createElement('script')
    script.src = 'https://www.youtube.com/iframe_api'
    document.head.appendChild(script)
  })
  return ytReady
}

async function loadYouTube(track: Track, startAt: number, autoplay: boolean) {
  const YT = await loadYouTubeApi()
  const params = { videoId: track.audio_source, startSeconds: startAt }
  if (yt) {
    autoplay ? yt.loadVideoById(params) : yt.cueVideoById(params)
    return
  }
  const el = document.createElement('div')
  ytHost.value!.replaceChildren(el)
  yt = new YT.Player(el, {
    width: '100%', height: '100%', videoId: track.audio_source,
    playerVars: { autoplay: autoplay ? 1 : 0, start: Math.floor(startAt), controls: 0, rel: 0, playsinline: 1 },
    events: {
      onReady: () => {
        yt.setVolume(player.volume * 100)
        if (autoplay) yt.playVideo()
      },
      onStateChange: (e: any) => {
        player.playing = e.data === YT.PlayerState.PLAYING
        player.loading = e.data === YT.PlayerState.BUFFERING
        const d = yt.getDuration?.()
        if (d) player.duration = d
      },
    },
  })
  clearInterval(ytTimer)
  ytTimer = setInterval(() => {
    if (player.track?.audio_type === 'youtube' && yt?.getCurrentTime) player.time = yt.getCurrentTime()
  }, 250)
}

const controller: PlayerController = {
  load(track, startAt, autoplay) {
    if (track.audio_type === 'hosted_file') {
      yt?.pauseVideo?.()
      const el = audio.value!
      el.src = track.audio_url!
      el.volume = player.volume
      el.currentTime = startAt
      if (autoplay) el.play().catch(() => (player.loading = false))
    } else if (track.audio_type === 'youtube') {
      audio.value?.pause()
      loadYouTube(track, startAt, autoplay)
    }
  },
  play() {
    if (player.track?.audio_type === 'youtube') yt?.playVideo?.()
    else audio.value?.play().catch(() => {})
  },
  pause() {
    if (player.track?.audio_type === 'youtube') yt?.pauseVideo?.()
    else audio.value?.pause()
  },
  seek(seconds) {
    if (player.track?.audio_type === 'youtube') yt?.seekTo?.(seconds, true)
    else if (audio.value) audio.value.currentTime = seconds
  },
  setVolume(volume) {
    if (audio.value) audio.value.volume = volume
    yt?.setVolume?.(volume * 100)
  },
}

onMounted(() => player.register(controller))
onBeforeUnmount(() => {
  player.register(null)
  clearInterval(ytTimer)
})
</script>

<style scoped>
.bar-enter-active, .bar-leave-active { transition: transform .4s cubic-bezier(.2, .8, .2, 1), opacity .4s; }
.bar-enter-from, .bar-leave-to { transform: translateY(100%); opacity: 0; }
</style>
