import type {
  Asset,
  AssetList,
  AssetPayload,
  AssetVersion,
  FilterOptions,
  ListParams,
} from '../types'

export class ApiError extends Error {
  status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
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

  downloadUrl: (assetId: number, versionId: number) =>
    `/api/assets/${assetId}/versions/${versionId}/download`,
}
