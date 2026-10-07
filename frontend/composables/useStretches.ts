import type { Stretch } from '~/components/AudioWave.vue'

/**
 * Stretches of an opus's recording, shared by its waveform (in the transport) and its discussion:
 * the stretch the reader has selected on the waveform, to comment on it, and the stretches that
 * comments already refer to, lit on the waveform.
 */
export function useStretches(opusId: string) {
  return {
    selection: useState<{ start: number; end: number } | null>(`stretch-selection-${opusId}`, () => null),
    commented: useState<Stretch[]>(`stretch-comments-${opusId}`, () => []),
  }
}

/** «01:20–01:45» */
export const formatStretch = (start: number, end: number) => `${formatTime(start)}–${formatTime(end)}`
