/**
 * A chat message as safe HTML: the text is escaped, links become links, @address leads to that hall,
 * line breaks stay. No markdown: chat messages are plain text.
 */
const escapeHtml = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')

// a link, or an @address not glued to a word or an e-mail (the same rule as the server's chat.service.MENTION)
const TOKEN = /(https?:\/\/[^\s<>"']+[^\s<>"'.,;:!?)\]])|(?<![\w.@])@([a-z0-9][a-z0-9._-]{1,30}[a-z0-9])/gi

export function renderChatText(text: string, me?: string | null): string {
  let html = ''
  let last = 0
  for (const m of text.matchAll(TOKEN)) {
    html += escapeHtml(text.slice(last, m.index))
    if (m[1]) {
      html += `<a href="${escapeHtml(m[1])}" target="_blank" rel="noopener nofollow ugc" class="link">${escapeHtml(m[1])}</a>`
    } else {
      const name = m[2].toLowerCase()
      html += `<a href="/@${escapeHtml(name)}" class="chat-mention${name === me ? ' is-me' : ''}">@${escapeHtml(m[2])}</a>`
    }
    last = (m.index || 0) + m[0].length
  }
  html += escapeHtml(text.slice(last))
  return html.replace(/\n/g, '<br>')
}

/** Does the message name this member? */
export const mentions = (text: string, username?: string | null) =>
  !!username && [...text.matchAll(TOKEN)].some((m) => m[2]?.toLowerCase() === username)
