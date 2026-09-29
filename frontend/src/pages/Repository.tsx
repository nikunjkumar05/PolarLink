import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { Asset, FilterOptions, ListParams } from '../types'
import { formatDate, formatBytes } from '../lib/format'

const PAGE_SIZE = 12

type FacetKey = 'asset_type' | 'expedition' | 'station' | 'topic' | 'year' | 'access_level'

const FACET_LABELS: Record<FacetKey, string> = {
  asset_type: 'Format',
  expedition: 'Expedition',
  station: 'Station',
  topic: 'Topic',
  year: 'Year',
  access_level: 'Access',
}

const ALL_FACETS: FacetKey[] = ['asset_type', 'expedition', 'station', 'topic', 'year', 'access_level']

function FacetGroup({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string
  options: (string | number)[]
  selected: (string | number)[]
  onToggle: (value: string | number) => void
}) {
  if (options.length === 0) return null
  return (
    <div className="facet">
      <h3>{label}</h3>
      <ul>
        {options.map((option) => {
          const key = String(option)
          const active = selected.some((value) => String(value) === key)
          return (
            <li key={key}>
              <label className={active ? 'facet-option active' : 'facet-option'}>
                <input type="checkbox" checked={active} onChange={() => onToggle(option)} />
                <span>{option}</span>
              </label>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default function Repository() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [filters, setFilters] = useState<Partial<Record<FacetKey, (string | number)[]>>>({})
  const [page, setPage] = useState(1)
  const [items, setItems] = useState<Asset[]>([])
  const [total, setTotal] = useState(0)
  const [options, setOptions] = useState<FilterOptions | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.getFilters().then(setOptions).catch(() => setOptions(null))
  }, [])

  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedQuery(query)
      setPage(1)
      setLoading(true)
    }, 300)
    return () => clearTimeout(handle)
  }, [query])

  const params: ListParams = useMemo(() => {
    const base: ListParams = { q: debouncedQuery || undefined, page, page_size: PAGE_SIZE }
    for (const key of ALL_FACETS) {
      const values = filters[key]
      if (values?.length) {
        if (key === 'year') base.year = values.map(Number)
        else (base[key] as string[]) = values.map(String)
      }
    }
    return base
  }, [debouncedQuery, filters, page])

  useEffect(() => {
    let cancelled = false
    api
      .listAssets(params)
      .then((result) => {
        if (cancelled) return
        setItems(result.items)
        setTotal(result.total)
        setError(null)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Failed to reach the repository API')
        setItems([])
        setTotal(0)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [params])

  const goToPage = (next: number) => {
    setPage(next)
    setLoading(true)
  }

  const toggle = (key: FacetKey, value: string | number) => {
    setFilters((current) => {
      const list = current[key] ?? []
      const next = list.some((entry) => String(entry) === String(value))
        ? list.filter((entry) => String(entry) !== String(value))
        : [...list, value]
      return { ...current, [key]: next }
    })
    setPage(1)
    setLoading(true)
  }

  const clearFilters = () => {
    setFilters({})
    setPage(1)
    setLoading(true)
  }

  const activeCount = ALL_FACETS.reduce((sum, key) => sum + (filters[key]?.length ?? 0), 0)
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const facetOptions = (key: FacetKey): (string | number)[] => {
    if (!options) return []
    switch (key) {
      case 'asset_type':
        return options.asset_types
      case 'access_level':
        return options.access_levels
      case 'expedition':
        return options.expeditions
      case 'station':
        return options.stations
      case 'topic':
        return options.topics
      case 'year':
        return options.years
    }
  }

  return (
    <div className="repository">
      <div className="repo-head">
        <div>
          <h1>Repository</h1>
          <p className="muted">
            {loading ? 'Loading…' : `${total} asset${total === 1 ? '' : 's'}`}
            {activeCount > 0 && ` · ${activeCount} filter${activeCount === 1 ? '' : 's'} applied`}
          </p>
        </div>
        <div className="repo-actions">
          <input
            ref={searchRef}
            className="search"
            type="search"
            placeholder="Search title, keywords, author…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Link className="btn primary" to="/upload">
            Upload asset
          </Link>
        </div>
      </div>

      <div className="repo-body">
        <aside className="facets">
          <div className="facet-head">
            <h2>Filters</h2>
            {activeCount > 0 && (
              <button className="link" onClick={clearFilters}>
                Clear all
              </button>
            )}
          </div>
          {ALL_FACETS.map((key) => (
            <FacetGroup
              key={key}
              label={FACET_LABELS[key]}
              options={facetOptions(key)}
              selected={filters[key] ?? []}
              onToggle={(value) => toggle(key, value)}
            />
          ))}
          {!options && <p className="muted small">Filter values unavailable.</p>}
        </aside>

        <section className="results">
          {error && <div className="banner error">{error}</div>}

          {!error && loading && <div className="banner">Loading repository…</div>}

          {!error && !loading && items.length === 0 && (
            <div className="banner empty">
              <p>No assets match this view.</p>
              <Link className="btn" to="/upload">
                Upload the first asset
              </Link>
            </div>
          )}

          {!error && items.length > 0 && (
            <div className="card-grid">
              {items.map((asset) => (
                <Link className="asset-card" key={asset.id} to={`/assets/${asset.id}`}>
                  <div className="asset-card-top">
                    <span className="chip">{asset.asset_type}</span>
                    <span className={`chip access-${asset.access_level.toLowerCase()}`}>
                      {asset.access_level}
                    </span>
                  </div>
                  <h3>{asset.title}</h3>
                  {asset.description && <p className="clamp">{asset.description}</p>}
                  <dl className="meta-grid">
                    {asset.expedition && (
                      <div>
                        <dt>Expedition</dt>
                        <dd>{asset.expedition}</dd>
                      </div>
                    )}
                    {asset.station && (
                      <div>
                        <dt>Station</dt>
                        <dd>{asset.station}</dd>
                      </div>
                    )}
                    {asset.year && (
                      <div>
                        <dt>Year</dt>
                        <dd>{asset.year}</dd>
                      </div>
                    )}
                    <div>
                      <dt>Versions</dt>
                      <dd>{asset.version_count}</dd>
                    </div>
                  </dl>
                  <footer>
                    <span>
                      {asset.latest_version
                        ? `${asset.latest_version.original_filename} · ${formatBytes(asset.latest_version.size_bytes)}`
                        : 'No file yet'}
                    </span>
                    <span>{formatDate(asset.updated_at)}</span>
                  </footer>
                </Link>
              ))}
            </div>
          )}

          {pages > 1 && (
            <div className="pager">
              <button className="btn" disabled={page <= 1} onClick={() => goToPage(page - 1)}>
                Previous
              </button>
              <span className="muted">
                Page {page} of {pages}
              </span>
              <button className="btn" disabled={page >= pages} onClick={() => goToPage(page + 1)}>
                Next
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
