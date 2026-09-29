/**
 * A schema.org block for search engines. Every "<" becomes the JSON escape "<" (six characters, starting
 * with a backslash), so no title or name can close the <script> it sits in: "</script><script>…" stays text.
 * In the regular expression replacement below the backslash is doubled on purpose — a single one would put
 * the "<" itself back.
 */
export const jsonLd = (data: Record<string, unknown>) => ({
  type: 'application/ld+json',
  innerHTML: JSON.stringify(data).replace(/</g, '\\u003c'),
})
