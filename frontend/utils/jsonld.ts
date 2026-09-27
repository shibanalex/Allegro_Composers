/** A schema.org block for search engines. "<" is escaped so a title can never close the <script> it sits in. */
export const jsonLd = (data: Record<string, unknown>) => ({
  type: 'application/ld+json',
  innerHTML: JSON.stringify(data).replace(/</g, '\u003c'),
})
