export type Role = 'composer' | 'theorist' | 'performer' | 'listener'
export type HallTheme = 'baroque' | 'romantic' | 'modern' | 'avantgarde'

export interface UserBrief {
  id: string
  username: string
  display_name: string
  pseudonym?: string | null
  avatar_url?: string | null
  role?: Role
}

export interface Link { label: string; url: string }

export type HallAccent = 'gold' | 'silver' | 'copper' | 'crimson' | 'emerald' | 'sapphire'
export type HallTab = 'exhibition' | 'library' | 'articles' | 'performances' | 'blog' | 'materials' | 'about'

export interface HallSettings {
  cover_url?: string | null
  epigraph?: string | null
  epigraph_source?: string | null
  accent?: HallAccent | null
  tabs?: HallTab[] | null
  pinned_post?: string | null
}

export interface Profile extends UserBrief {
  bio?: string | null
  about_md?: string | null
  links: Link[]
  role: Role
  hall_theme: HallTheme
  hall: HallSettings
  created_at: string
  stats?: Partial<Record<'opuses' | 'performances' | 'posts' | 'articles', number>>
}

export interface Me extends Profile {
  email?: string | null
  is_admin: boolean
  is_moderator?: boolean
  capabilities: string[]
  seen_hints?: string[]
}

export interface SiteConfig {
  setup_available: boolean
  roles: Record<string, string>
  hall_themes: Record<string, string>
}

export interface Marker { page_number: number; timestamp_seconds: number }

export interface MeasureMarker { measure_number: number; timestamp_seconds: number }

export interface Opus {
  id: string
  slug: string
  title: string
  subtitle?: string | null
  genre: string
  instruments: string[]
  key_signature?: string | null
  year?: number | null
  description_md?: string | null
  cover_url?: string | null
  audio_type: 'none' | 'youtube' | 'hosted_file'
  audio_source?: string | null
  audio_url?: string | null
  audio_duration_seconds?: number | null
  score_url?: string | null
  score_file_key?: string | null
  musicxml_file_key?: string | null
  score_page_count?: number | null
  score_access: 'free' | 'view_only' | 'paid'
  musicxml_url?: string | null
  audio_offset_seconds: number
  auto_page_markers: boolean
  status: 'published' | 'draft' | 'unlisted'
  featured: boolean
  play_count: number
  created_at: string
  author: UserBrief
  markers: Marker[]
  measure_markers: MeasureMarker[]
  critique_count: number
}

export interface Attachment { url: string; name: string; content_type: string; size?: number | null }

export interface OpusBrief {
  id: string
  slug: string
  title: string
  subtitle?: string | null
  audio_type: Opus['audio_type']
  audio_source?: string | null
  audio_url?: string | null
  audio_duration_seconds?: number | null
  cover_url?: string | null
  author: UserBrief
}

/** A post as another post shows it: a quotation, a mention */
export interface PostBrief {
  id: string
  slug: string
  kind: Post['kind']
  title: string
  preview: string
  image_url?: string | null
  created_at: string
  author: UserBrief
}

export interface Reactions { count: number; mine: boolean }

export interface Post {
  id: string
  slug: string
  kind: 'article' | 'note' | 'sketch' | 'news' | 'workshop'
  title: string
  excerpt?: string | null
  content_md: string
  cover_url?: string | null
  attachments: Attachment[]
  tags: string[]
  status: string
  view_count: number
  created_at: string
  author: UserBrief
  opus?: OpusBrief | null
  quote?: PostBrief | null
  /** Sketches: the author asks for feedback */
  seeking_feedback?: boolean
  comment_count: number
}

export interface Comment {
  id: string
  opus_id?: string | null
  post_id?: string | null
  parent_id?: string | null
  timestamp_marker?: number | null
  content_md: string
  created_at: string
  author: UserBrief
}

export interface Collection {
  id: string
  slug: string
  title: string
  description?: string | null
  year?: number | null
  created_at: string
  author: UserBrief
  opuses: Opus[]
}

export interface Page<T> { items: T[]; total: number }

export interface Facet { value: string; label: string; count: number }
export interface Facets { genres: Facet[]; instruments: Facet[]; keys: Facet[] }

export interface Uploaded { key: string; url: string; name: string; content_type: string; size: number }

export interface Material {
  id: string
  kind: 'book' | 'link' | 'file'
  title: string
  description?: string | null
  url?: string | null
  file?: Attachment | null
  cover_url?: string | null
  position: number
  created_at: string
}

export interface Performance {
  id: string
  title: string
  composer_name?: string | null
  opus?: OpusBrief | null
  description_md?: string | null
  audio_type: 'youtube' | 'hosted_file'
  audio_source?: string | null
  audio_url?: string | null
  audio_duration_seconds?: number | null
  recorded_year?: number | null
  status: 'published' | 'draft' | 'unlisted'
  play_count: number
  created_at: string
  performer: UserBrief
}

export interface Feedback {
  id: string
  kind: 'idea' | 'bug' | 'other'
  title: string
  body: string
  status: 'new' | 'planned' | 'done' | 'declined'
  reply_md?: string | null
  replied_at?: string | null
  created_at: string
  author: UserBrief
}

export interface AccessLink {
  id: string
  purpose: 'reset'
  note?: string | null
  created_at: string
  expires_at: string
  used_at?: string | null
  revoked_at?: string | null
  target_user?: UserBrief | null
  token?: string | null
  status: 'active' | 'used' | 'expired' | 'revoked'
}

export interface AdminUser extends UserBrief {
  is_admin: boolean
  is_moderator?: boolean
  is_hidden: boolean
  has_email: boolean
  created_at: string
}

/** One entry of the main feed: exactly one of opus / performance / post */
export interface FeedEntry {
  type: 'opus' | 'performance' | 'post'
  created_at: string
  opus?: Opus | null
  performance?: Performance | null
  post?: Post | null
  likes: Reactions
  /** The last comments (works and posts) */
  comments?: { id: string; parent_id?: string | null; content_md: string; created_at: string; author: UserBrief }[]
}
