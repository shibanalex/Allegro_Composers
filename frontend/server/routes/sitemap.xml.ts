// Map of every public page for search engines: composers' halls, works, posts. Built from the API on request.
interface Dated { created_at: string }
interface Page<T> { items: T[]; total: number }

const PAGE = 100
const MAX = 5000 // plenty for years; the sitemap format allows 50 000 addresses

const escape = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

export default defineEventHandler(async (event) => {
  const api = String(useRuntimeConfig(event).apiInternal)
  const origin = siteOrigin(event)

  async function all<T>(path: string): Promise<T[]> {
    const items: T[] = []
    while (items.length < MAX) {
      const page = await $fetch<Page<T>>(`${api}${path}`, { query: { limit: PAGE, offset: items.length } })
      items.push(...page.items)
      if (!page.items.length || items.length >= page.total) break
    }
    return items
  }

  const [composers, opuses, posts] = await Promise.all([
    all<{ username: string } & Dated>('/api/users'),
    all<{ slug: string } & Dated>('/api/opuses'),
    all<{ slug: string } & Dated>('/api/posts'),
  ])

  const day = (iso: string) => iso.slice(0, 10)
  const urls = [
    { loc: '/', priority: '1.0' },
    { loc: '/about', priority: '0.5' },
    { loc: '/members', priority: '0.6' },
    ...composers.map((c) => ({ loc: `/@${c.username}`, priority: '0.9' })),
    ...opuses.map((o) => ({ loc: `/opus/${o.slug}`, lastmod: day(o.created_at), priority: '0.8' })),
    ...posts.map((p) => ({ loc: `/posts/${p.slug}`, lastmod: day(p.created_at), priority: '0.6' })),
  ]

  setHeader(event, 'Content-Type', 'application/xml; charset=utf-8')
  setHeader(event, 'Cache-Control', 'public, max-age=3600')
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...urls.map((u) =>
      `  <url><loc>${escape(origin + u.loc)}</loc>${u.lastmod ? `<lastmod>${u.lastmod}</lastmod>` : ''}<priority>${u.priority}</priority></url>`),
    '</urlset>',
    '',
  ].join('\n')
})
