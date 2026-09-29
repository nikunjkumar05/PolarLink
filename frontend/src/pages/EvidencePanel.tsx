import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { AssetVersion, EvidencePassage } from '../types'

const ACTIVE: string[] = ['PENDING', 'PROCESSING']

interface Props {
  assetId: number
  versions: AssetVersion[]
  onChange: () => void
}

export default function EvidencePanel({ assetId, versions, onChange }: Props) {
  const [versionId, setVersionId] = useState<number>(versions.at(-1)?.id ?? 0)
  const [items, setItems] = useState<EvidencePassage[]>([])
  const [total, setTotal] = useState(0)
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const [pageNumber, setPageNumber] = useState<number | null>(null)
  const [pages, setPages] = useState<number[]>([])
  const [openId, setOpenId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const version = versions.find((entry) => entry.id === versionId) ?? versions.at(-1)
  const processing = version ? ACTIVE.includes(version.processing_status) : false

  const debouncedRef = useRef(debounced)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    debouncedRef.current = debounced
  }, [debounced])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (query === debouncedRef.current) return
      setDebounced(query)
      setLoading(true)
    }, 300)
    return () => window.clearTimeout(handle)
  }, [query])

  const refresh = useCallback(() => setReloadKey((key) => key + 1), [])

  useEffect(() => {
    if (!version) return
    let cancelled = false
    void (async () => {
      try {
        const result = await api.listPassages(version.id, {
          q: debounced || undefined,
          page_number: pageNumber ?? undefined,
          page_size: 200,
        })
        const pageList = await api.listPages(version.id)
        if (cancelled) return
        setItems(result.items)
        setTotal(result.total)
        setPages(pageList)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Failed to load evidence passages')
        setItems([])
        setTotal(0)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [version, debounced, pageNumber, reloadKey])

  // Poll while the selected version is still being processed (FR-06 is async).
  useEffect(() => {
    if (!processing || !version) return
    const handle = window.setInterval(() => {
      refresh()
      void api.getAsset(assetId).then(onChange)
    }, 1500)
    return () => window.clearInterval(handle)
  }, [processing, version, refresh, assetId, onChange])

  async function reprocess() {
    if (!version) return
    setBusy(true)
    setLoading(true)
    setError(null)
    try {
      await api.reprocess(version.id)
      onChange()
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Reprocessing failed')
      setLoading(false)
    } finally {
      setBusy(false)
    }
  }

  if (versions.length === 0) {
    return (
      <section className="panel">
        <h2>Evidence passages</h2>
        <p className="muted">No source versions yet.</p>
      </section>
    )
  }

  return (
    <section className="panel evidence">
      <div className="panel-head">
        <h2>Evidence passages</h2>
        <div className="evidence-controls">
          <select
            value={version?.id ?? ''}
            onChange={(event) => {
              const next = Number(event.target.value)
              if (next === versionId) return
              setVersionId(next)
              setPageNumber(null)
              setOpenId(null)
              setLoading(true)
            }}
          >
            {versions.map((entry) => (
              <option key={entry.id} value={entry.id}>
                v{entry.version_number} · {entry.passage_count} passages
              </option>
            ))}
          </select>
          <input
            type="search"
            placeholder="Search passages…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="btn small" onClick={() => void reprocess()} disabled={busy || processing}>
            {busy ? 'Queued…' : 'Reprocess'}
          </button>
        </div>
      </div>

      {version && (
        <p className="muted small evidence-meta">
          {version.original_filename} · {version.passage_count} passages over{' '}
          {version.page_count ?? '—'} page{version.page_count === 1 ? '' : 's'}
          {version.processing_note && <span className="note"> · {version.processing_note}</span>}
        </p>
      )}

      {processing && version && (
        <div className="banner">Processing v{version.version_number} — extracting text…</div>
      )}
      {version?.processing_error && (
        <div className="banner error">Processing failed: {version.processing_error}</div>
      )}
      {error && <div className="banner error">{error}</div>}
      {loading && !processing && <div className="banner">Loading passages…</div>}

      {pages.length > 1 && (
        <div className="page-jump">
          <button
            className={!pageNumber ? 'pill active' : 'pill'}
            onClick={() => {
              if (pageNumber === null) return
              setPageNumber(null)
              setLoading(true)
            }}
          >
            All
          </button>
          {pages.map((page) => (
            <button
              key={page}
              className={pageNumber === page ? 'pill active' : 'pill'}
              onClick={() => {
                setPageNumber(pageNumber === page ? null : page)
                setLoading(true)
              }}
            >
              p{page}
            </button>
          ))}
        </div>
      )}

      {!loading && !processing && items.length === 0 && (
        <div className="banner empty">
          <p>
            {debounced || pageNumber
              ? 'No passages match this view.'
              : 'No text was extracted from this version.'}
          </p>
        </div>
      )}

      <ul className="passage-list">
        {items.map((passage) => {
          const open = openId === passage.id
          return (
            <li key={passage.id} className={open ? 'passage open' : 'passage'}>
              <button
                className="passage-head"
                onClick={() => setOpenId(open ? null : passage.id)}
              >
                <span className="loc">
                  {passage.page_number ? `p.${passage.page_number}` : passage.location_type}
                </span>
                <span className="seq">#{passage.sequence_number}</span>
                <span className={open ? 'snippet' : 'snippet clamped'}>
                  {passage.content.replace(/\s+/g, ' ').trim()}
                </span>
              </button>
              {open && (
                <div className="passage-body">
                  <pre>{passage.content}</pre>
                  <dl className="passage-meta">
                    <div>
                      <dt>Chars</dt>
                      <dd>{passage.char_count}</dd>
                    </div>
                    <div>
                      <dt>Offsets</dt>
                      <dd>
                        {passage.start_offset}–{passage.end_offset}
                      </dd>
                    </div>
                    <div>
                      <dt>Location</dt>
                      <dd>
                        {passage.location_type}
                        {passage.page_number ? ` · page ${passage.page_number}` : ''}
                      </dd>
                    </div>
                    <div>
                      <dt>Evidence ID</dt>
                      <dd>E{passage.id}</dd>
                    </div>
                  </dl>
                </div>
              )}
            </li>
          )
        })}
      </ul>

      <p className="muted small">
        {total > 0 ? `${total} passage${total === 1 ? '' : 's'} in this version` : ''}
      </p>
    </section>
  )
}
