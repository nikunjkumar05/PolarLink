import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api, ApiError } from '../api/client'
import { formatDate } from '../lib/format'
import { useAuth } from '../lib/useAuth'
import type { Claim, ClaimList } from '../types'

const STATUSES = ['ALL', 'SUPPORTED', 'VERIFIED', 'STALE', 'DISPUTED', 'DRAFT']

export default function Claims() {
  const { user, can } = useAuth()
  const [claims, setClaims] = useState<Claim[]>([])
  const [total, setTotal] = useState(0)
  const [status, setStatus] = useState('ALL')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

const applyClaims = useCallback((data: ClaimList) => {
    setClaims(data.items)
    setTotal(data.total)
    setError(null)
    setLoading(false)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      applyClaims(await api.listClaims(status === 'ALL' ? {} : { status }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not load claims')
      setLoading(false)
    }
  }, [status, applyClaims])

  useEffect(() => {
    let cancelled = false
    const params = status === 'ALL' ? {} : { status }
    api
      .listClaims(params)
      .then((data) => {
        if (!cancelled) applyClaims(data)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'could not load claims')
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [status, applyClaims])

  async function setClaimStatus(claim: Claim, next: string) {
    setBusyId(claim.id)
    try {
      await api.setClaimStatus(claim.id, next, `Marked ${next.toLowerCase()} by ${user?.name ?? 'editor'}`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not update the claim')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Claims</h1>
          <p className="muted">
            Every claim must cite at least one evidence passage — that rule is enforced by the API, not
            just the form.
          </p>
        </div>
        <div className="row-actions">
          <label className="field inline">
            <span>Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value.toLowerCase()}
                </option>
              ))}
            </select>
          </label>
          <span className="small muted">{total} claim(s)</span>
        </div>
      </div>

      {!user && (
        <p className="note-box">
          You are browsing signed out. <Link className="link" to="/login">Sign in</Link> to create or
          review claims.
        </p>
      )}
      {error && <p className="error-box">{error}</p>}
      {loading && <p className="muted">Loading claims…</p>}
      {!loading && claims.length === 0 && (
        <p className="muted">
          No claims yet. Open a search result and use <strong>Claim this passage</strong> to create the
          first one.
        </p>
      )}

      <div className="claim-list">
        {claims.map((claim) => (
          <article key={claim.id} className="panel claim-card">
            <div className="claim-head">
              <span className={`pill status-${claim.status.toLowerCase()}`}>{claim.status.toLowerCase()}</span>
              {claim.topic && <span className="chip">{claim.topic}</span>}
              <span className="small muted">#{claim.id}</span>
              <span className="small muted">created {formatDate(claim.created_at)}</span>
            </div>

            <p className="claim-text">{claim.text}</p>

            <div className="evidence-block">
              {claim.evidence_links.map((link) => (
                <div key={link.id} className={`evidence-row${link.passage_missing ? ' missing' : ''}`}>
                  <div className="evidence-meta">
                    <span className={`chip relation-${link.relation.toLowerCase()}`}>{link.relation.toLowerCase()}</span>
                    {link.evidence ? (
                      <>
                        <Link
                          className="link"
                          to={`/assets/${link.evidence.asset_id}?v=${link.evidence.version_id}&passage=${link.evidence.passage_id}`}
                        >
                          {link.evidence.asset_title}
                        </Link>
                        <span className="small muted">
                          v{link.evidence.version_number} · p.{link.evidence.page_number ?? '—'} · E
                          {link.evidence.passage_id}
                        </span>
                      </>
                    ) : (
                      <span className="small muted">This passage no longer exists in the archive.</span>
                    )}
                  </div>
                  {link.evidence && <p className="excerpt">{link.evidence.excerpt}</p>}
                </div>
              ))}
            </div>

            {can('REVIEWER') && claim.status !== 'VERIFIED' && (
              <div className="row-actions">
                <button
                  className="btn small"
                  disabled={busyId === claim.id}
                  onClick={() => setClaimStatus(claim, 'SUPPORTED')}
                >
                  Accept
                </button>
                <button
                  className="btn small"
                  disabled={busyId === claim.id}
                  onClick={() => setClaimStatus(claim, 'DISPUTED')}
                >
                  Dispute
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}