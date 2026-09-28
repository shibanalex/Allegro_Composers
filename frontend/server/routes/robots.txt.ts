// Search engines: index the public site, skip the owner's and technical pages
export default defineEventHandler((event) => {
  setHeader(event, 'Content-Type', 'text/plain; charset=utf-8')
  return [
    'User-agent: *',
    'Disallow: /login',
    'Disallow: /register',
    'Disallow: /setup',
    'Disallow: /settings',
    'Disallow: /create',
    'Disallow: /admin',
    'Disallow: /reset',
    'Disallow: /api/',
    '',
    `Sitemap: ${siteOrigin(event)}/sitemap.xml`,
    '',
  ].join('\n')
})
