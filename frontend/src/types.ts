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
