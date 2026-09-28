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

export interface Profile extends UserBrief {
  bio?: string | null
  about_md?: string | null
  links: Link[]
  role: Role
  hall_theme: HallTheme
  created_at: string
  stats?: Partial<Record<'opuses' | 'performances' | 'posts' | 'articles', number>>
}

export interface Me extends Profile {
  email?: string | null
  is_admin: boolean
  capabilities: string[]
}

export interface SiteConfig {
  registration: 'closed' | 'invite' | 'open'
  registration_open: boolean
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
  instrumentation?: string | null
  ensemble: string
  form: string
  key_signature?: string | null
  difficulty?: number | null
  year?: number | null
  tags: string[]
  description_md?: string | null
  cover_url?: string | null
  audio_type: 'none' | 'youtube' | 'hosted_file'
  audio_source?: string | null
  audio_url?: string | null
  audio_duration_seconds?: number | null
  score_url?: string | null
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
  author: UserBrief
}

export interface Post {
  id: string
  slug: string
  kind: 'article' | 'note' | 'news' | 'workshop'
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
export interface Facets { ensembles: Facet[]; forms: Facet[]; keys: Facet[]; difficulty: Facet[]; tags: Facet[] }

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
  purpose: 'invite' | 'reset'
  note?: string | null
  role?: Role | null
  created_at: string
  expires_at: string
  used_at?: string | null
  revoked_at?: string | null
  used_by?: UserBrief | null
  target_user?: UserBrief | null
  token?: string | null
  status: 'active' | 'used' | 'expired' | 'revoked'
}

export interface AdminUser extends UserBrief {
  is_admin: boolean
  is_hidden: boolean
  has_email: boolean
  created_at: string
}
