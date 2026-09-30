import type {
  AlertList,
  AlertPassage,
  Article,
  ArticleList,
  Asset,
  AssetList,
  AssetPayload,
  AssetVersion,
  Capabilities,
  Claim,
  ClaimList,
  FilterOptions,
  ImpactAlert,
  ListParams,
  LoginResponse,
  PassageList,
  ReviewEvent,
  SearchParams,
  SearchResponse,
  User,
} from '../types'

const TOKEN_KEY = 'polarlink.token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init?.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(path, { ...init, headers })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
      else if (Array.isArray(body?.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join('; ')
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

function queryString(params: ListParams): string {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  for (const key of ['asset_type', 'expedition', 'station', 'topic', 'access_level'] as const) {
    for (const value of params[key] ?? []) search.append(key, value)
  }
  for (const value of params.year ?? []) search.append('year', String(value))
  if (params.page) search.set('page', String(params.page))
  if (params.page_size) search.set('page_size', String(params.page_size))
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  listAssets: (params: ListParams = {}) => request<AssetList>(`/api/assets${queryString(params)}`),

  getFilters: () => request<FilterOptions>('/api/assets/filters'),

  getAsset: (id: number) => request<Asset>(`/api/assets/${id}`),

  createAsset: (file: File, meta: AssetPayload) => {
    const form = new FormData()
    form.append('file', file)
    form.append('meta', JSON.stringify(meta))
    return request<Asset>('/api/assets', { method: 'POST', body: form })
  },

  createVersion: (assetId: number, file: File, note?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (note) form.append('note', note)
    return request<AssetVersion>(`/api/assets/${assetId}/versions`, { method: 'POST', body: form })
  },

  updateAsset: (id: number, patch: Partial<AssetPayload>) =>
    request<Asset>(`/api/assets/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    }),

  deleteAsset: (id: number) => request<void>(`/api/assets/${id}`, { method: 'DELETE' }),

  listPassages: (versionId: number, params: { q?: string; page_number?: number; page?: number; page_size?: number } = {}) => {
    const search = new URLSearchParams()
    if (params.q) search.set('q', params.q)
    if (params.page_number) search.set('page_number', String(params.page_number))
    if (params.page) search.set('page', String(params.page))
    if (params.page_size) search.set('page_size', String(params.page_size))
    const qs = search.toString()
    return request<PassageList>(`/api/versions/${versionId}/passages${qs ? `?${qs}` : ''}`)
  },

  listPages: (versionId: number) => request<number[]>(`/api/versions/${versionId}/pages`),

  search: (params: SearchParams = {}) => {
    const search = new URLSearchParams()
    search.set('q', params.q ?? '')
    search.set('mode', params.mode ?? 'hybrid')
    if (params.limit) search.set('limit', String(params.limit))
    for (const key of ['asset_type', 'expedition', 'station', 'topic', 'access_level'] as const) {
      for (const value of params[key] ?? []) search.append(key, value)
    }
    for (const value of params.year ?? []) search.append('year', String(value))
    return request<SearchResponse>(`/api/search?${search.toString()}`)
  },

  reprocess: (versionId: number) =>
    request<AssetVersion>(`/api/versions/${versionId}/reprocess`, { method: 'POST' }),

  downloadUrl: (assetId: number, versionId: number) =>
    `/api/assets/${assetId}/versions/${versionId}/download`,

  // ---------------------------------------------------------------- identity
  login: (email: string, password: string) =>
    request<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>('/api/auth/me'),

  directory: () => request<User[]>('/api/auth/directory'),

  capabilities: () => request<Capabilities>('/api/capabilities'),

  // ---------------------------------------------------------------- claims
  listClaims: (params: { status?: string; topic?: string; q?: string } = {}) => {
    const search = new URLSearchParams()
    if (params.status) search.set('status', params.status)
    if (params.topic) search.set('topic', params.topic)
    if (params.q) search.set('q', params.q)
    const qs = search.toString()
    return request<ClaimList>(`/api/claims${qs ? `?${qs}` : ''}`)
  },

  getClaim: (id: number) => request<Claim>(`/api/claims/${id}`),

  createClaim: (payload: { text: string; topic?: string | null; evidence: { passage_id: number; relation?: string }[] }) =>
    request<Claim>('/api/claims', { method: 'POST', body: JSON.stringify(payload) }),

  setClaimStatus: (id: number, status: string, comment?: string) => {
    const search = new URLSearchParams({ status })
    if (comment) search.set('comment', comment)
    return request<Claim>(`/api/claims/${id}/status?${search.toString()}`, { method: 'POST' })
  },

  claimEvents: (id: number) => request<ReviewEvent[]>(`/api/claims/${id}/events`),

  // ---------------------------------------------------------------- articles
  listArticles: (status?: string) =>
    request<ArticleList>(`/api/articles${status ? `?status=${status}` : ''}`),

  getArticle: (id: number) => request<Article>(`/api/articles/${id}`),

  createArticle: (payload: { title: string; summary?: string | null; audience?: string | null; claim_ids: number[] }) =>
    request<Article>('/api/articles', { method: 'POST', body: JSON.stringify(payload) }),

  regenerate: (id: number, mode: string) =>
    request<Article>(`/api/articles/${id}/generate`, {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),

  transition: (id: number, target: string, comment?: string) =>
    request<Article>(`/api/articles/${id}/transition?target=${target}`, {
      method: 'POST',
      body: JSON.stringify({ comment: comment ?? null }),
    }),

  articleEvents: (id: number) => request<ReviewEvent[]>(`/api/articles/${id}/events`),

  publicArticle: (slug: string) => request<Article>(`/api/articles/by-slug/${slug}`),

  // ---------------------------------------------------------------- alerts
  listAlerts: (params: { status?: string; article_id?: number } = {}) => {
    const search = new URLSearchParams()
    if (params.status) search.set('status', params.status)
    if (params.article_id) search.set('article_id', String(params.article_id))
    const qs = search.toString()
    return request<AlertList>(`/api/alerts${qs ? `?${qs}` : ''}`)
  },

  resolveAlert: (id: number, payload: { status: string; note?: string | null; current_passage_id?: number | null }) =>
    request<ImpactAlert>(`/api/alerts/${id}/resolve`, { method: 'POST', body: JSON.stringify(payload) }),

  alertPassages: (id: number) => request<AlertPassage[]>(`/api/alerts/${id}/passages`),

  assetChanges: (assetId: number) => request<Record<string, unknown>>(`/api/alerts/asset/${assetId}/changes`),
}
