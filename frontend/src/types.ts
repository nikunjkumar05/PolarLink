export type AssetType = 'PDF' | 'IMAGE' | 'VIDEO' | 'DATASET' | 'ACTIVITY' | 'OTHER'
export type AccessLevel = 'PUBLIC' | 'INTERNAL' | 'RESTRICTED'
export type ProcessingStatus = 'PENDING' | 'PROCESSING' | 'DONE' | 'FAILED'

export interface AssetVersion {
  id: number
  asset_id: number
  version_number: number
  original_filename: string
  file_hash: string
  size_bytes: number
  mime_type: string | null
  page_count: number | null
  passage_count: number
  processing_status: ProcessingStatus
  processing_error: string | null
  processing_note: string | null
  note: string | null
  uploaded_at: string
}

export type LocationType = 'PAGE' | 'TIMESTAMP' | 'TABLE' | 'TEXT'

export interface EvidencePassage {
  id: number
  asset_version_id: number
  asset_id: number
  sequence_number: number
  location_type: LocationType
  content: string
  page_number: number | null
  start_offset: number | null
  end_offset: number | null
  char_count: number
  created_at: string
}

export interface PassageList {
  total: number
  page: number
  page_size: number
  version: AssetVersion
  items: EvidencePassage[]
}

export interface Asset {
  id: number
  title: string
  description: string | null
  asset_type: AssetType
  topic: string | null
  expedition: string | null
  station: string | null
  year: number | null
  author: string | null
  keywords: string | null
  attribution: string | null
  source: string | null
  access_level: AccessLevel
  created_at: string
  updated_at: string
  version_count: number
  latest_version: AssetVersion | null
  versions?: AssetVersion[]
}

export interface AssetList {
  total: number
  page: number
  page_size: number
  items: Asset[]
}

export interface FilterOptions {
  asset_types: string[]
  access_levels: string[]
  expeditions: string[]
  stations: string[]
  topics: string[]
  years: number[]
}

export interface AssetPayload {
  title: string
  description?: string | null
  asset_type?: AssetType
  topic?: string | null
  expedition?: string | null
  station?: string | null
  year?: number | null
  author?: string | null
  keywords?: string | null
  attribution?: string | null
  source?: string | null
  access_level?: AccessLevel
  note?: string | null
}

export interface ListParams {
  q?: string
  asset_type?: string[]
  expedition?: string[]
  station?: string[]
  topic?: string[]
  year?: number[]
  access_level?: string[]
  page?: number
  page_size?: number
}

export type SearchMode = 'hybrid' | 'keyword' | 'semantic'

export interface SearchParams extends ListParams {
  mode?: SearchMode
  limit?: number
}

export interface SearchIndex {
  keyword_ready: boolean
  keyword_rows: number
  total_passages: number
  embedded_passages: number
  embedding_model: string | null
  embedding_ready: boolean
  embedding_error: string | null
}

export interface SearchHit {
  rank: number
  score: number
  sources: string[]
  keyword_rank: number | null
  semantic_rank: number | null
  keyword_score: number | null
  semantic_score: number | null
  passage: EvidencePassage
  asset: Asset
  version: { id: number; version_number: number }
}

export interface SearchResponse {
  query: string
  mode: SearchMode
  took_ms: number
  total: number
  limit: number
  items: SearchHit[]
  index: SearchIndex
  note: string | null
}

// ---------------------------------------------------------------- editorial

export type Role = 'ADMIN' | 'EDITOR' | 'REVIEWER'

export interface User {
  id: number
  email: string
  name: string
  role: Role
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export type ClaimStatus = 'DRAFT' | 'SUPPORTED' | 'DISPUTED' | 'REJECTED' | 'STALE' | 'VERIFIED'

export interface EvidenceRef {
  id: number
  passage_id: number
  asset_id: number
  asset_title: string
  version_id: number
  version_number: number
  page_number: number | null
  excerpt: string
}

export interface ClaimEvidenceLink {
  id: number
  relation: string
  quote: string | null
  evidence: EvidenceRef | null
  passage_missing: boolean
}

export interface Claim {
  id: number
  text: string
  topic: string | null
  status: ClaimStatus
  created_by_id: number | null
  verified_at: string | null
  created_at: string
  updated_at: string
  evidence_links: ClaimEvidenceLink[]
}

export interface ClaimList {
  total: number
  items: Claim[]
}

export interface ReviewEvent {
  id: number
  action: string
  comment: string | null
  from_status: string | null
  to_status: string | null
  actor_name: string | null
  created_at: string
}

export type ArticleStatus = 'DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'PUBLISHED' | 'REJECTED'

export interface ArticleSummary {
  id: number
  title: string
  slug: string
  status: ArticleStatus
  summary: string | null
  audience: string | null
  author_id: number | null
  author_name: string | null
  generation_mode: string | null
  needs_reverification: boolean
  claim_count: number
  open_alert_count: number
  created_at: string
  updated_at: string
  published_at: string | null
}

export interface Article extends ArticleSummary {
  body: string | null
  generation_model: string | null
  generation_note: string | null
  claims: { position: number; claim: Claim }[]
  open_alerts: number[]
}

export interface ArticleList {
  total: number
  items: ArticleSummary[]
}

export type AlertStatus = 'OPEN' | 'REVERIFIED' | 'ACKNOWLEDGED'

export interface ImpactAlert {
  id: number
  article_id: number | null
  article_title: string | null
  claim_id: number
  claim_text: string
  asset_id: number
  asset_title: string
  previous_version_id: number
  previous_version_number: number
  current_version_id: number
  current_version_number: number
  previous_quote: string | null
  current_quote: string | null
  current_page_number: number | null
  previous_passage_id: number | null
  current_passage_id: number | null
  change_kind: string
  reason: string
  status: AlertStatus
  resolution_note: string | null
  resolved_at: string | null
  resolved_by_name: string | null
  created_at: string
}

export interface AlertList {
  total: number
  open_total: number
  items: ImpactAlert[]
}

export interface AlertPassage {
  id: number
  page_number: number | null
  sequence_number: number
  excerpt: string
}

export interface Capabilities {
  llm_available: boolean
  default_mode: string
}
