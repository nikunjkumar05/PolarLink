import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api, ApiError } from '../api/client'
import { formatDate } from '../lib/format'
import { useAuth } from '../lib/useAuth'
import type { ArticleList, ArticleSummary, Capabilities, Claim, ClaimList } from '../types'

export default function Articles() {
  const { user, can } = useAuth()
  const [articles, setArticles] = useState<ArticleSummary[]>([])
  const [claims, setClaims] = useState<Claim[]>([])
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [selected, setSelected] = useState<number[]>([])
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(true)
  const [building, setBuilding] = useState(false)
  const [error, setError] = useState<string | null>(null)

const applyData = useCallback((articleData: ArticleList, claimData: ClaimList) => {
    setArticles(articleData.items)
    setClaims(claimData.items.filter((c) => c.status !== 'REJECTED' && c.status !== 'DRAFT'))
    setError(null)
    setLoading(false)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [articleData, claimData] = await Promise.all([api.listArticles(), api.listClaims()])
      applyData(articleData, claimData)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not load articles')
      setLoading(false)
    }
  }, [applyData])

  useEffect(() => {
    let cancelled = false
    Promise.all([api.listArticles(), api.listClaims()])
      .then(([articleData, claimData]) => {
        if (!cancelled) applyData(articleData, claimData)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'could not load articles')
        setLoading(false)
      })
    api.capabilities().then((value) => !cancelled && setCapabilities(value)).catch(() => null)
    return () => {
      cancelled = true
    }
  }, [applyData])

  function toggle(claimId: number) {
    setSelected((current) =>
      current.includes(claimId) ? current.filter((id) => id !== claimId) : [...current, claimId],
    )
  }

  async function build(event: React.FormEvent) {
    event.preventDefault()
    if (selected.length === 0) {
      setError('Pick at least one claim — an article is assembled from claims, never free text.')
      return
    }
    setBuilding(true)
    setError(null)
    try {
      const article = await api.createArticle({
        title: title.trim(),
        summary: summary.trim() || null,
        claim_ids: selected,
      })
      setTitle('')
      setSummary('')
      setSelected([])
      await load()
      window.location.assign(`/articles/${article.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not build the article')
    } finally {
      setBuilding(false)
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Articles</h1>
          <p className="muted">
            Outreach content assembled from claims. Every sentence traces back to a source passage.
          </p>
        </div>
        {capabilities && (
          <span className="chip">
            drafting: {capabilities.llm_available ? 'LLM' : 'extractive (no API key)'}
          </span>
        )}
      </div>

      {error && <p className="error-box">{error}</p>}

      {can('EDITOR') && (
        <form className="panel builder" onSubmit={build}>
          <h2>Build an article</h2>
          <div className="builder-grid">
            <label className="field">
              <span>Title</span>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="What did the 2024 fox survey find?"
                minLength={8}
                required
              />
            </label>
            <label className="field">
              <span>Summary</span>
              <input
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="One line for the reader"
              />
            </label>
          </div>

          <p className="small muted">
            Pick the claims to include — {selected.length} selected
          </p>
          <div className="claim-picker">
            {claims.length === 0 && <p className="muted">No usable claims yet.</p>}
            {claims.map((claim) => (
              <label key={claim.id} className={`pick-row${selected.includes(claim.id) ? ' on' : ''}`}>
                <input
                  type="checkbox"
                  checked={selected.includes(claim.id)}
                  onChange={() => toggle(claim.id)}
                />
                <span className="claim-text small">{claim.text}</span>
                <span className={`pill status-${claim.status.toLowerCase()}`}>{claim.status.toLowerCase()}</span>
                <span className="small muted">
                  {claim.evidence_links.length} evidence ·{' '}
                  {claim.evidence_links[0]?.evidence?.asset_title ?? 'source missing'}
                </span>
              </label>
            ))}
          </div>

          <button className="btn primary" type="submit" disabled={building || selected.length === 0}>
            {building ? 'Composing…' : 'Generate draft'}
          </button>
        </form>
      )}

      {!user && (
        <p className="note-box">
          <Link className="link" to="/login">
            Sign in
          </Link>{' '}
          as an editor to build articles.
        </p>
      )}

      {loading && <p className="muted">Loading articles…</p>}
      {!loading && articles.length === 0 && <p className="muted">No articles yet.</p>}

      <div className="card-grid">
        {articles.map((article) => (
          <article key={article.id} className="asset-card">
            <div className="row-actions">
              <span className={`pill status-${article.status.toLowerCase()}`}>
                {article.status.toLowerCase().replace('_', ' ')}
              </span>
              {article.needs_reverification && (
                <span className="chip warn">re-verification required</span>
              )}
            </div>
            <h3>
              <Link to={`/articles/${article.id}`}>{article.title}</Link>
            </h3>
            {article.summary && <p className="small muted">{article.summary}</p>}
            <p className="small muted">
              {article.claim_count} claim(s) · {article.generation_mode ?? '—'}
              {article.author_name ? ` · ${article.author_name}` : ''}
            </p>
            {article.published_at && (
              <p className="small muted">published {formatDate(article.published_at)}</p>
            )}
            {article.open_alert_count > 0 && (
              <p className="small warn">
                {article.open_alert_count} open alert(s) —{' '}
                <Link className="link" to="/alerts">
                  review
                </Link>
              </p>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}