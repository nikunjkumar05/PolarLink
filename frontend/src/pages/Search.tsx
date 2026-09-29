import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { FilterOptions, SearchMode, SearchParams, SearchResponse } from '../types'

const LIMIT = 20

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

const MODES: { value: SearchMode; label: string; hint: string }[] = [
  { value: 'hybrid', label: 'Hybrid', hint: 'Keyword + semantic, fused (FR-10/11)' },
  { value: 'keyword', label: 'Keyword', hint: 'FTS5 BM25 exact and stemmed terms' },
  { value: 'semantic', label: 'Semantic', hint: 'Embedding similarity — same meaning, different words' },
]

const EXAMPLES = [
  'frozen ocean surface measurements',
  'coastal transect',
  'how many fox kits were born',
  'ozone depletion altitude',
]

function resultLink(hit: SearchResponse['items'][number]) {
  return `/assets/${hit.asset.id}?v=${hit.version.id}&passage=${hit.passage.id}`
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState('')
  const [mode, setMode] = useState<SearchMode>('hybrid')
  const [filters, setFilters] = useState<Partial<Record<FacetKey, string | number>>>({})
  const [options, setOptions] = useState<FilterOptions | null>(null)
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getFilters().then(setOptions).catch(() => setOptions(null))
  }, [])

  useEffect(() => {
    // Only arm the debounce when the text actually differs, otherwise loading
    // is set true with no follow-up request and the banner never clears.
    if (query === submitted) return
    const handle = window.setTimeout(() => {
      setLoading(true)
      setSubmitted(query)
    }, 300)
    return () => window.clearTimeout(handle)
  }, [query, submitted])

  const params = useMemo(() => {
    const base: SearchParams = { q: submitted, mode, limit: LIMIT }
    for (const key of ALL_FACETS) {
      const value = filters[key]
      if (value === undefined) continue
      if (key === 'year') base.year = [Number(value)]
      else (base[key] as string[]) = [String(value)]
    }
    return base
  }, [submitted, mode, filters])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const response = await api.search(params)
        if (cancelled) return
        setResult(response)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Search failed')
        setResult(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [params])

  const setFacet = (key: FacetKey, value: string | number) => {
    setFilters((current) => {
      const next = { ...current }
      if (String(current[key]) === String(value)) delete next[key]
      else next[key] = value
      return next
    })
    setLoading(true)
  }

  const activeCount = ALL_FACETS.reduce((sum, key) => sum + (filters[key] !== undefined ? 1 : 0), 0)
  const index = result?.index
  const note = loading ? null : (error ?? result?.note ?? null)

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
    <div className="repository search-page">
      <div className="repo-head">
        <div>
          <h1>Search</h1>
          <p className="muted">
            {result
              ? `${result.total} passage${result.total === 1 ? '' : 's'} · ${result.took_ms} ms`
              : 'Search across every extracted evidence passage'}
          </p>
        </div>
      </div>

      <div className="search-bar">
        <input
          className="search big"
          type="search"
          placeholder="Ask in plain language — e.g. frozen ocean surface measurements"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          autoFocus
        />
        <div className="mode-switch" role="group" aria-label="Search mode">
          {MODES.map((entry) => (
            <button
              key={entry.value}
              className={mode === entry.value ? 'mode active' : 'mode'}
              title={entry.hint}
              onClick={() => {
                setMode(entry.value)
                setLoading(true)
              }}
            >
              {entry.label}
            </button>
          ))}
        </div>
      </div>

      <div className="examples">
        <span className="muted small">Try:</span>
        {EXAMPLES.map((example) => (
          <button key={example} className="pill" onClick={() => setQuery(example)}>
            {example}
          </button>
        ))}
      </div>

      {index && (
        <div className="index-bar muted small">
          {index.total_passages} passages indexed · {index.keyword_rows} keyword rows (FTS5) ·{' '}
          {index.embedded_passages} embedded
          {index.embedding_model ? ` · ${index.embedding_model}` : ''}
          {!index.embedding_ready && index.embedding_error
            ? ` · semantic unavailable: ${index.embedding_error}`
            : ''}
        </div>
      )}

      <div className="repo-body">
        <aside className="facets">
          <div className="facet-head">
            <h2>Filters</h2>
            {activeCount > 0 && (
              <button className="link" onClick={() => setFilters({})}>
                Clear all
              </button>
            )}
          </div>
          {ALL_FACETS.map((key) => {
            const values = facetOptions(key)
            if (values.length === 0) return null
            return (
              <div className="facet" key={key}>
                <h3>{FACET_LABELS[key]}</h3>
                <ul>
                  {values.map((value) => {
                    const active = String(filters[key]) === String(value)
                    return (
                      <li key={String(value)}>
                        <label className={active ? 'facet-option active' : 'facet-option'}>
                          <input
                            type="checkbox"
                            checked={active}
                            onChange={() => setFacet(key, value)}
                          />
                          <span>{value}</span>
                        </label>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )
          })}
          {!options && <p className="muted small">Filter values unavailable.</p>}
        </aside>

        <section className="results">
          {note && <div className={error ? 'banner error' : 'banner'}>{note}</div>}
          {loading && <div className="banner">Searching…</div>}

          {!loading && result && result.items.length === 0 && !note && (
            <div className="banner empty">
              <p>No passages match this query.</p>
            </div>
          )}

          <ol className="hit-list">
            {result?.items.map((hit) => (
              <li key={hit.passage.id} className="hit">
                <div className="hit-head">
                  <span className="rank">#{hit.rank}</span>
                  {hit.sources.map((source) => (
                    <span key={source} className={`chip source-${source}`}>
                      {source}
                    </span>
                  ))}
                  <span className="chip">{hit.asset.asset_type}</span>
                  <span className={`chip access-${hit.asset.access_level.toLowerCase()}`}>
                    {hit.asset.access_level}
                  </span>
                  <span className="muted small score">score {hit.score.toFixed(4)}</span>
                </div>

                <Link className="hit-title" to={resultLink(hit)}>
                  {hit.asset.title}
                </Link>

                <p className="hit-snippet">{hit.passage.content.replace(/\s+/g, ' ').trim()}</p>

                <div className="hit-foot muted small">
                  <span>
                    v{hit.version.version_number}
                    {hit.passage.page_number ? ` · p.${hit.passage.page_number}` : ''} · E
                    {hit.passage.id}
                  </span>
                  {hit.keyword_rank != null && <span>keyword rank {hit.keyword_rank}</span>}
                  {hit.semantic_rank != null && <span>semantic rank {hit.semantic_rank}</span>}
                  {hit.asset.expedition && <span>{hit.asset.expedition}</span>}
                  {hit.asset.station && <span>{hit.asset.station}</span>}
                  <Link className="btn small" to={resultLink(hit)}>
                    Open evidence
                  </Link>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  )
}
