import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api, ApiError } from '../api/client'
import { formatDate } from '../lib/format'
import { useAuth } from '../lib/useAuth'
import type { Article, Capabilities, ReviewEvent } from '../types'

const NEXT_STEP: Record<string, { label: string; target: string; needsReviewer: boolean }> = {
  DRAFT: { label: 'Submit for review', target: 'IN_REVIEW', needsReviewer: false },
  IN_REVIEW: { label: 'Approve', target: 'APPROVED', needsReviewer: true },
  APPROVED: { label: 'Publish', target: 'PUBLISHED', needsReviewer: true },
  REJECTED: { label: 'Back to draft', target: 'DRAFT', needsReviewer: false },
  PUBLISHED: { label: 'Unpublish', target: 'APPROVED', needsReviewer: true },
}

export default function ArticleDetail() {
  const { id } = useParams()
  const articleId = Number(id)
  const { user, can } = useAuth()
  const [article, setArticle] = useState<Article | null>(null)
  const [events, setEvents] = useState<ReviewEvent[]>([])
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

const applyArticle = useCallback((data: Article, trail: ReviewEvent[]) => {
    setArticle(data)
    setEvents(trail)
    setError(null)
    setLoading(false)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getArticle(articleId)
      applyArticle(data, await api.articleEvents(articleId))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not load the article')
      setLoading(false)
    }
  }, [articleId, applyArticle])

  useEffect(() => {
    let cancelled = false
    api
      .getArticle(articleId)
      .then(async (data) => {
        const trail = await api.articleEvents(articleId)
        if (!cancelled) applyArticle(data, trail)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'could not load the article')
        setLoading(false)
      })
    api.capabilities().then((value) => !cancelled && setCapabilities(value)).catch(() => null)
    return () => {
      cancelled = true
    }
  }, [articleId, applyArticle])

  async function act(target: string) {
    setBusy(true)
    setError(null)
    try {
      await api.transition(articleId, target, comment.trim() || undefined)
      setComment('')
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not update the article')
    } finally {
      setBusy(false)
    }
  }

  async function regenerate(mode: string) {
    setBusy(true)
    setError(null)
    try {
      await api.regenerate(articleId, mode)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not regenerate the draft')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <div className="page"><p className="muted">Loading article…</p></div>
  if (!article) {
    return (
      <div className="page">
        <p className="error-box">{error ?? 'article not found'}</p>
        <Link className="link" to="/articles">Back to articles</Link>
      </div>
    )
  }

  const step = NEXT_STEP[article.status]
  const allowed = step && (step.needsReviewer ? can('REVIEWER') : can('EDITOR'))

  return (
    <div className="page">
      <p className="crumb">
        <Link className="link" to="/articles">Articles</Link> / #{article.id}
      </p>

      <div className="page-head">
        <div>
          <h1>{article.title}</h1>
          <div className="row-actions">
            <span className={`pill status-${article.status.toLowerCase()}`}>
              {article.status.toLowerCase().replace('_', ' ')}
            </span>
            {article.needs_reverification && (
              <span className="chip warn">re-verification required</span>
            )}
            <span className="small muted">
              {article.claim_count} claim(s) · drafted by {article.generation_mode ?? '—'}
              {article.author_name ? ` · ${article.author_name}` : ''}
            </span>
          </div>
        </div>
        {article.status === 'PUBLISHED' && (
          <Link className="btn" to={`/read/${article.slug}`}>
            Open public page
          </Link>
        )}
      </div>

      {error && <p className="error-box">{error}</p>}

      <div className="review-grid">
        <section className="panel">
          <h2>Draft</h2>
          {article.generation_note && <p className="small muted">{article.generation_note}</p>}
          <div className="body-preview">
            {(article.body ?? '').split('\n\n').map((paragraph, index) => (
              <p key={index}>{paragraph.replace(/^#\s*/, '')}</p>
            ))}
          </div>
          {can('EDITOR') && (
            <div className="row-actions">
              <button className="btn small" disabled={busy} onClick={() => regenerate('extractive')}>
                Recompose extractively
              </button>
              {capabilities?.llm_available && (
                <button className="btn small" disabled={busy} onClick={() => regenerate('llm')}>
                  Redraft with LLM
                </button>
              )}
            </div>
          )}
        </section>

        <section className="panel">
          <h2>Workflow</h2>
          {user ? (
            <>
              <label className="field">
                <span>Note for the audit trail (optional)</span>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={2}
                  placeholder="Checked against the source passage."
                />
              </label>
              <div className="row-actions">
                {step && (
                  <button
                    className="btn primary"
                    disabled={busy || !allowed}
                    title={!allowed ? 'This step needs a different role' : undefined}
                    onClick={() => act(step.target)}
                  >
                    {step.label}
                  </button>
                )}
                {article.status === 'IN_REVIEW' && can('REVIEWER') && (
                  <button className="btn" disabled={busy} onClick={() => act('REJECTED')}>
                    Reject
                  </button>
                )}
              </div>
              {!allowed && step && (
                <p className="small muted">
                  {step.needsReviewer
                    ? 'A reviewer has to sign this off.'
                    : 'Only an editor can move the draft forward.'}
                </p>
              )}
            </>
          ) : (
            <p className="small muted">
              <Link className="link" to="/login">Sign in</Link> to move this article through review.
            </p>
          )}
          {article.published_at && (
            <p className="small muted">published {formatDate(article.published_at)}</p>
          )}

          <h3>Audit trail</h3>
          <ol className="timeline">
            {events.map((event) => (
              <li key={event.id}>
                <span className="small muted">{formatDate(event.created_at)}</span>{' '}
                <strong>{event.action.toLowerCase().replace('_', ' ')}</strong>{' '}
                <span className="small muted">
                  {event.actor_name ?? 'system'}
                  {event.from_status && event.to_status
                    ? ` · ${event.from_status.toLowerCase()} → ${event.to_status.toLowerCase()}`
                    : ''}
                </span>
                {event.comment && <p className="small">{event.comment}</p>}
              </li>
            ))}
          </ol>
        </section>
      </div>

      <section className="panel">
        <h2>Claims and their evidence</h2>
        {article.open_alerts.length > 0 && (
          <p className="warn-box">
            {article.open_alerts.length} impact alert(s) pending —{' '}
            <Link className="link" to="/alerts">
              open the re-verification inbox
            </Link>
          </p>
        )}
        <div className="claim-list">
          {article.claims.map(({ position, claim }) => (
            <article key={claim.id} className="claim-card">
              <div className="claim-head">
                <span className="small muted">#{position + 1}</span>
                <span className={`pill status-${claim.status.toLowerCase()}`}>
                  {claim.status.toLowerCase()}
                </span>
                {claim.topic && <span className="chip">{claim.topic}</span>}
              </div>
              <p className="claim-text">{claim.text}</p>
              {claim.evidence_links.map((link) => (
                <div key={link.id} className={`evidence-row${link.passage_missing ? ' missing' : ''}`}>
                  <div className="evidence-meta">
                    <span className={`chip relation-${link.relation.toLowerCase()}`}>
                      {link.relation.toLowerCase()}
                    </span>
                    {link.evidence ? (
                      <>
                        <Link
                          className="link"
                          to={`/assets/${link.evidence.asset_id}?v=${link.evidence.version_id}&passage=${link.evidence.passage_id}`}
                        >
                          {link.evidence.asset_title}
                        </Link>
                        <span className="small muted">
                          v{link.evidence.version_number} · p{link.evidence.page_number ?? '—'} · E
                          {link.evidence.passage_id}
                        </span>
                      </>
                    ) : (
                      <span className="small muted">passage no longer in the archive</span>
                    )}
                  </div>
                  {link.evidence && <p className="excerpt">{link.evidence.excerpt}</p>}
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}