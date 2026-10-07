"""Draw the waveforms (core.peaks) of recordings uploaded before waveforms existed.

Idempotent: a recording that already has its waveform (or a mark that it can't be read) is skipped,
so the container runs it on every start (start.sh) and it costs one listing of the storage folders.

    python -m scripts.make_peaks
"""
from allegro.core import peaks
from allegro.core.storage import storage


def main() -> None:
    made = failed = 0
    for folder in peaks.AUDIO_FOLDERS:
        keys = set(storage.keys(folder))
        for key in sorted(keys):
            if not peaks.is_audio(key) or peaks.peaks_key(key) in keys:
                continue
            try:
                ok = peaks.make(key)
            except Exception as e:  # one broken file must not stop the rest
                ok = False
                print(f"  {key}: {e}")
            made, failed = (made + 1, failed) if ok else (made, failed + 1)
    print(f"Waveforms: made {made}, failed {failed}")


if __name__ == "__main__":
    main()
