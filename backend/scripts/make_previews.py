"""Make the light previews (core.images) for pictures uploaded before previews existed.

Idempotent: a picture that already has its preview is skipped, so the container runs it on every
start (start.sh) and it costs one listing of the storage folders.

    python -m scripts.make_previews
"""
from allegro.core import images
from allegro.core.storage import storage


def main() -> None:
    made = failed = 0
    for folder in images.PICTURE_FOLDERS:
        keys = set(storage.keys(folder))
        for key in sorted(keys):
            if not images.is_picture(key) or images.preview_key(key) in keys:
                continue
            try:
                preview = images.make_preview(storage.read_bytes(key))
            except Exception as e:  # one broken file must not stop the rest
                failed += 1
                print(f"  {key}: {e}")
                continue
            if preview:
                storage.save_bytes(images.preview_key(key), preview)
                made += 1
    print(f"Previews: made {made}, failed {failed}")


if __name__ == "__main__":
    main()
