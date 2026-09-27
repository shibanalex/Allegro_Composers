export interface UserBrief {
  id: string
  username: string
  display_name: string
  pseudonym?: string | null
  avatar_url?: string | null
}

export interface Link { label: string; url: string }

export interface Profile extends UserBrief {
  bio?: string | null
  about_md?: string | null
  links: Link[]
  created_at: string
  stats?: { opuses: number; posts: number; collections: number }
}

export interface Me extends Profile { email: string }

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
  kind: 'article' | 'note' | 'workshop'
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
