import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api, ApiError } from '../api/client'
import { formatDate } from '../lib/format'
import { useAuth } from '../lib/useAuth'
import type { AlertList, AlertPassage, ImpactAlert } from '../types'

export default function Alerts() {
  const { user, can } = useAuth()
  const [alerts, setAlerts] = useState<ImpactAlert[]>([])
  const [openTotal, setOpenTotal] = useState(0)
  const [filter, setFilter] = useState('OPEN')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [candidates, setCandidates] = useState<Record<number, AlertPassage[]>>({})
  const [notes, setNotes] = useState<Record<number, string>>({})
  const [chosen, setChosen] = useState<Record<number, number | null>>({})
  const [error, setError] = useState<string | null>(null)

const applyAlerts = useCallback((data: AlertList) => {
    setAlerts(data.items)
    setOpenTotal(data.open_total)
    setError(null)
    setLoading(false)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      applyAlerts(await api.listAlerts(filter === 'ALL' ? {} : { status: filter }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not load alerts')
      setLoading(false)
    }
  }, [filter, applyAlerts])

  useEffect(() => {
    let cancelled = false
    const params = filter === 'ALL' ? {} : { status: filter }
    api
      .listAlerts(params)
      .then((data) => {
        if (!cancelled) applyAlerts(data)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'could not load alerts')
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [filter, applyAlerts])

  async function open(alert: ImpactAlert) {
    if (expanded === alert.id) {
      setExpanded(null)
      return
    }
    setExpanded(alert.id)
    if (!candidates[alert.id]) {
      try {
        const passages = await api.alertPassages(alert.id)
        setCandidates((current) => ({ ...current, [alert.id]: passages }))
      } catch {
        setCandidates((current) => ({ ...current, [alert.id]: [] }))
      }
    }
  }

  async function resolve(alert: ImpactAlert, status: string) {
    setBusyId(alert.id)
    setError(null)
    try {
      await api.resolveAlert(alert.id, {
        status,
        note: notes[alert.id]?.trim() || null,
        current_passage_id: chosen[alert.id] ?? null,
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'could not resolve the alert')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Re-verification inbox</h1>
          <p className="muted">
            Raised automatically when a re-uploaded source changes a passage a published claim depends on.
          </p>
        </div>
        <div className="row-actions">
          <label className="field inline">
            <span>Show</span>
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              {['OPEN', 'REVERIFIED', 'ACKNOWLEDGED', 'ALL'].map((value) => (
                <option key={value} value={value}>
                  {value.toLowerCase()}
                </option>
              ))}
            </select>
          </label>
          <span className={openTotal > 0 ? 'chip warn' : 'chip'}>{openTotal} open</span>
        </div>
      </div>

      {!user && (
        <p className="note-box">
          <Link className="link" to="/login">Sign in</Link> as a reviewer to close alerts.
        </p>
      )}
      {error && <p className="error-box">{error}</p>}
      {loading && <p className="muted">Loading alerts…</p>}
      {!loading && alerts.length === 0 && <p className="muted">Nothing to re-verify. </p>}

      <div className="claim-list">
        {alerts.map((alert) => (
          <article key={alert.id} className="panel alert-card">
            <div className="claim-head">
              <span className={`pill status-${alert.status.toLowerCase()}`}>
                {alert.status.toLowerCase()}
              </span>
              <span className="chip">{alert.change_kind.toLowerCase()}</span>
              <span className="small muted">{formatDate(alert.created_at)}</span>
            </div>

            <h3>{alert.reason}</h3>

            <p className="small muted">
              Source: <Link className="link" to={`/assets/${alert.asset_id}`}>{alert.asset_title}</Link> — v
              {alert.previous_version_number} → v{alert.current_version_number}
              {alert.article_id && (
                <>
                  {' · article: '}
                  <Link className="link" to={`/articles/${alert.article_id}`}>
                    {alert.article_title ?? `#${alert.article_id}`}
                  </Link>
                </>
              )}
            </p>

            <div className="diff-grid">
              <div className="diff-col before">
                <span className="small muted">What the claim cited (v{alert.previous_version_number})</span>
                <p>{alert.previous_quote ?? '—'}</p>
              </div>
              <div className="diff-col after">
                <span className="small muted">
                  What the source says now (v{alert.current_version_number}
                  {alert.current_page_number ? `, p${alert.current_page_number}` : ''})
                </span>
                <p>{alert.current_quote ?? 'This passage was removed from the new version.'}</p>
              </div>
            </div>

            <p className="claim-text">
              <strong>Claim:</strong> {alert.claim_text}
            </p>

            {alert.status === 'OPEN' ? (
              <>
                <button className="btn small" onClick={() => open(alert)}>
                  {expanded === alert.id ? 'Hide candidates' : 'Choose the passage that still supports it'}
                </button>

                {expanded === alert.id && (
                  <div className="panel candidate-list">
                    {(candidates[alert.id] ?? []).map((passage) => (
                      <label key={passage.id} className="pick-row">
                        <input
                          type="radio"
                          name={`passage-${alert.id}`}
                          checked={(chosen[alert.id] ?? null) === passage.id}
                          onChange={() =>
                            setChosen((current) => ({ ...current, [alert.id]: passage.id }))
                          }
                        />
                        <span className="small">
                          p{passage.page_number ?? '—'} · E{passage.id}
                        </span>
                        <span className="small muted">{passage.excerpt}</span>
                      </label>
                    ))}
                    {(candidates[alert.id] ?? []).length === 0 && (
                      <p className="small muted">Loading passages…</p>
                    )}
                  </div>
                )}

                <label className="field">
                  <span>Reviewer note</span>
                  <textarea
                    rows={2}
                    value={notes[alert.id] ?? ''}
                    onChange={(e) => setNotes((current) => ({ ...current, [alert.id]: e.target.value }))}
                    placeholder="Claim still holds — the edit was cosmetic."
                  />
                </label>

                <div className="row-actions">
                  <button
                    className="btn primary"
                    disabled={!can('REVIEWER') || busyId === alert.id}
                    onClick={() => resolve(alert, 'REVERIFIED')}
                  >
                    Re-verify
                  </button>
                  <button
                    className="btn"
                    disabled={!can('REVIEWER') || busyId === alert.id}
                    onClick={() => resolve(alert, 'ACKNOWLEDGED')}
                  >
                    Acknowledge only
                  </button>
                </div>
              </>
            ) : (
              <p className="small muted">
                Closed {formatDate(alert.resolved_at)} by {alert.resolved_by_name ?? 'system'}
                {alert.resolution_note ? ` — ${alert.resolution_note}` : ''}
              </p>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}