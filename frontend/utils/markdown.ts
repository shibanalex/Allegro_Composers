import { Marked } from 'marked'

const escapeHtml = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

const SAFE_HREF = /^(https?:\/\/|mailto:|\/(?![\/\\])|#)/i

// "02:15" / "1:02:15" outside of other digits → clickable timecode
const TIMECODE = /(?<![\d:])(\d{1,2}(?::[0-5]\d){1,2})(?![\d:])/g

const marked = new Marked({
  gfm: true,
  breaks: true,
  renderer: {
    // Raw HTML from authors is shown as text - no XSS through posts or comments
    html({ text }) {
      return escapeHtml(text)
    },
    link({ href, title, tokens }) {
      const text = this.parser.parseInline(tokens)
      if (href.startsWith('#t=')) {
        return `<button type="button" class="timecode" data-t="${Number(href.slice(3))}">${text}</button>`
      }
      if (!SAFE_HREF.test(href)) return text
      const external = /^https?:/i.test(href)
      return `<a href="${escapeHtml(href)}"${title ? ` title="${escapeHtml(title)}"` : ''}${external ? ' target="_blank" rel="noopener nofollow"' : ''}>${text}</a>`
    },
    image({ href, text }) {
      if (!SAFE_HREF.test(href)) return escapeHtml(text)
      return `<img src="${escapeHtml(href)}" alt="${escapeHtml(text)}" loading="lazy">`
    },
  },
})

/** Markdown → safe HTML. With timecodes=true, "02:15" becomes a button[data-t] that seeks the player. */
export function renderMarkdown(text = '', { timecodes = false } = {}) {
  let source = text
  if (timecodes) {
    source = source.replace(TIMECODE, (match) => {
      const seconds = match.split(':').map(Number).reduce((acc, p) => acc * 60 + p, 0)
      return `[${match}](#t=${seconds})`
    })
  }
  return marked.parse(source, { async: false }) as string
}

/** Plain-text preview of markdown */
export const stripMarkdown = (text = '', max = 220) => {
  const plain = text.replace(/[#>*_`\[\]()!]/g, '').replace(/\s+/g, ' ').trim()
  return plain.length > max ? plain.slice(0, max) + '…' : plain
}
