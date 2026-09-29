import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { SearchHit, SearchIndex } from '../types'

const PREVIEW_QUERY = 'sea ice'

const STEPS = [
  {
    step: '01',
    title: 'Ingest',
    body: 'A report, dataset or photograph becomes a versioned asset. The stored file is hashed and never modified.',
    action: 'Upload a PDF',
    to: '/upload',
  },
  {
    step: '02',
    title: 'Extract',
    body: 'Text is read page by page and cut into page-aware evidence passages that keep their page number.',
  },
  {
    step: '03',
    title: 'Index',
    body: 'Each passage gets an FTS5 BM25 keyword row plus a 384-dimension embedding stored beside it.',
  },
  {
    step: '04',
    title: 'Retrieve',
    body: 'Keyword and semantic ranks are fused, so the answer arrives as a passage with a link to its source.',
    action: 'Ask a question',
    to: '/search',
  },
]

const AC_CHECKS = [
  { id: 'AC-01', text: 'An authorized user can upload a PDF', to: '/upload', label: 'Try the upload' },
  { id: 'AC-02', text: 'The PDF becomes searchable', to: '/search', label: 'Search it' },
  { id: 'AC-03', text: 'A query retrieves the relevant passage', to: '/search', label: 'See results' },
  { id: 'AC-04', text: 'The search result identifies the correct page', to: '/search', label: 'See page numbers' },
  { id: 'AC-05', text: 'Selecting the result opens the supporting source', to: '/repository', label: 'Open a document' },
]

export default function Landing() {
  const [assetTotal, setAssetTotal] = useState<number | null>(null)
  const [index, setIndex] = useState<SearchIndex | null>(null)
  const [preview, setPreview] = useState<SearchHit | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const list = await api.listAssets({ page_size: 1 })
        if (!cancelled) setAssetTotal(list.total)
      } catch {
        if (!cancelled) setAssetTotal(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const result = await api.search({ q: PREVIEW_QUERY, mode: 'hybrid', limit: 1 })
        if (cancelled) return
        setIndex(result.index)
        setPreview(result.items[0] ?? null)
      } catch {
        if (!cancelled) setIndex(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const rawSnippet = preview ? preview.passage.content.replace(/\s+/g, ' ').trim() : ''
  const previewSnippet = rawSnippet.length > 170 ? `${rawSnippet.slice(0, 170)}…` : rawSnippet

  return (
    <div className="landing">
      <section className="hero">
        <div className="hero-copy">
          <span className="chip">SIH26063 · NCPOR</span>
          <h1>Every answer, linked back to the page it came from.</h1>
          <p className="muted">
            PolarLink archives polar expedition reports, datasets and photographs, then answers a
            plain-language question with the exact evidence passage — and the source document behind
            it.
          </p>
          <div className="hero-actions">
            <Link className="btn primary" to="/search">
              Ask a question
            </Link>
            <Link className="btn" to="/upload">
              Upload a PDF
            </Link>
            <Link className="btn" to="/repository">
              Browse repository
            </Link>
          </div>
          <dl className="hero-stats">
            <div>
              <dt>Assets</dt>
              <dd>{assetTotal ?? '—'}</dd>
            </div>
            <div>
              <dt>Passages indexed</dt>
              <dd>{index ? index.total_passages : '—'}</dd>
            </div>
            <div>
              <dt>Retrieval mode</dt>
              <dd>Hybrid</dd>
            </div>
            <div>
              <dt>Embeddings</dt>
              <dd>{index?.embedding_ready ? 'Ready' : 'Local, on demand'}</dd>
            </div>
          </dl>
        </div>

        <div className="hero-preview">
          <div className="preview-q">
            <span className="preview-label">Live query</span>
            <p>“{PREVIEW_QUERY}”</p>
          </div>
          <div className="preview-arrow">↓ hybrid retrieval over the seeded corpus</div>
          {preview ? (
            <Link
              className="preview-hit-link"
              to={`/assets/${preview.asset.id}?v=${preview.version.id}&passage=${preview.passage.id}`}
            >
              <div className="hit preview-hit">
                <div className="hit-head">
                  <span className="rank">#1</span>
                  {preview.sources.map((source) => (
                    <span key={source} className={`chip source-${source}`}>
                      {source}
                    </span>
                  ))}
                  <span className="muted small score">score {preview.score.toFixed(4)}</span>
                </div>
                <span className="hit-title">{preview.asset.title}</span>
                <p className="hit-snippet">{previewSnippet}</p>
                <div className="hit-foot muted small">
                  <span>
                    v{preview.version.version_number}
                    {preview.passage.page_number ? ` · p.${preview.passage.page_number}` : ''} · E
                    {preview.passage.id}
                  </span>
                  <span className="btn small">Open evidence</span>
                </div>
              </div>
            </Link>
          ) : (
            <div className="hit preview-hit muted small">Loading a live result…</div>
          )}
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-head">
          <h2>From a PDF to a cited answer</h2>
          <p className="muted small">
            The pipeline the prototype runs end to end — no manual steps between upload and evidence.
          </p>
        </div>
        <div className="steps">
          {STEPS.map((item) => (
            <div className="step" key={item.step}>
              <span className="step-num">{item.step}</span>
              <h3>{item.title}</h3>
              <p className="muted small">{item.body}</p>
              {item.to && item.action && (
                <Link className="link" to={item.to}>
                  {item.action} →
                </Link>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-head">
          <h2>What this prototype demonstrates</h2>
          <p className="muted small">
            Acceptance criteria covered by Modules 1–3: repository, upload, processing and hybrid
            search.
          </p>
        </div>
        <ul className="ac-list">
          {AC_CHECKS.map((item) => (
            <li key={item.id}>
              <span className="ac-id">{item.id}</span>
              <span>{item.text}</span>
              <Link className="link" to={item.to}>
                {item.label} →
              </Link>
            </li>
          ))}
        </ul>
        <p className="muted small scope-note">
          Content generation, review workflow and source-update detection are specified in the
          requirements document and are not built in this prototype.
        </p>
      </section>
    </div>
  )
}
