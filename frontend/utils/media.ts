// Every uploaded picture has a light WebP copy beside it (backend: allegro/core/images.py):
// images/<user>/<name>.jpg → images/<user>/<name>.jpg.preview.webp
const PICTURE = /\/(images|covers)\/[^/]+\/[^/]+\.(jpe?g|png|webp|avif)$/i

/** The preview of an uploaded picture; any other address is returned as it is */
export function previewOf(url: string): string {
  return PICTURE.test(url) ? `${url}.preview.webp` : url
}
