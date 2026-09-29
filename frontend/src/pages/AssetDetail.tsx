import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { Asset, AssetVersion } from '../types'
import { formatDate, formatBytes, shortHash } from '../lib/format'
import EvidencePanel from './EvidencePanel'

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="meta-row">
      <dt>{label}</dt>
      <dd>{value || <span className="muted">—</span>}</dd>
    </div>
  )
}

export default function AssetDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const assetId = Number(id)
  const fileRef = useRef<HTMLInputElement>(null)

  const [asset, setAsset] = useState<Asset | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<Partial<Asset>>({})
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [flash, setFlash] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  // FR-14 — arriving from a search result deep-links the exact passage.
  const [searchParams] = useSearchParams()
  const targetVersionId = Number(searchParams.get('v')) || undefined
  const targetPassageId = Number(searchParams.get('passage')) || undefined

  const load = useCallback(() => setReloadKey((key) => key + 1), [])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const data = await api.getAsset(assetId)
        if (cancelled) return
        setAsset(data)
        setDraft(data)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Failed to load asset')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [assetId, reloadKey])

  async function save() {
    setBusy(true)
    setError(null)
    try {
      const updated = await api.updateAsset(assetId, {
        title: draft.title,
        description: draft.description,
        topic: draft.topic,
        expedition: draft.expedition,
        station: draft.station,
        year: draft.year,
        author: draft.author,
        keywords: draft.keywords,
        attribution: draft.attribution,
        source: draft.source,
      })
      setAsset(updated)
      setDraft(updated)
      setEditing(false)
      setFlash('Metadata saved')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }

  async function addVersion(file: File) {
    setBusy(true)
    setLoading(true)
    setError(null)
    try {
      await api.createVersion(assetId, file, note || undefined)
      setNote('')
      setFlash(`Version uploaded as v${(asset?.version_count ?? 0) + 1}`)
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Version upload failed')
      setLoading(false)
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function remove() {
    if (!window.confirm(`Delete "${asset?.title}" and all of its versions?`)) return
    setBusy(true)
    try {
      await api.deleteAsset(assetId)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Delete failed')
      setBusy(false)
    }
  }

  if (loading) return <div className="banner">Loading asset…</div>
  if (error && !asset) return <div className="banner error">{error}</div>
  if (!asset) return null

  const versions: AssetVersion[] = asset.versions ?? []

  return (
    <div className="detail">
      <div className="page-head">
        <div>
          <Link className="crumb" to="/">
            ← Repository
          </Link>
          <h1>{asset.title}</h1>
          <div className="chip-row">
            <span className="chip">{asset.asset_type}</span>
            <span className={`chip access-${asset.access_level.toLowerCase()}`}>
              {asset.access_level}
            </span>
            <span className="chip">{versions.length} version{versions.length === 1 ? '' : 's'}</span>
          </div>
        </div>
        <div className="repo-actions">
          <button className="btn" onClick={() => setEditing((value) => !value)} disabled={busy}>
            {editing ? 'Cancel edit' : 'Edit metadata'}
          </button>
          <button className="btn danger" onClick={remove} disabled={busy}>
            Delete
          </button>
        </div>
      </div>

      {flash && (
        <div className="banner success" onClick={() => setFlash(null)}>
          {flash}
        </div>
      )}
      {error && <div className="banner error">{error}</div>}

      <div className="detail-grid">
        <section className="panel">
          <h2>Metadata</h2>
          {editing ? (
            <div className="form-grid">
              <label className="field">
                <span className="field-label">Title</span>
                <input value={draft.title ?? ''} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
              </label>
              <label className="field">
                <span className="field-label">Description</span>
                <textarea rows={3} value={draft.description ?? ''} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
              </label>
              <label className="field">
                <span className="field-label">Topic</span>
                <input value={draft.topic ?? ''} onChange={(e) => setDraft({ ...draft, topic: e.target.value })} />
              </label>
              <label className="field">
                <span className="field-label">Expedition</span>
                <input value={draft.expedition ?? ''} onChange={(e) => setDraft({ ...draft, expedition: e.target.value })} />
              </label>
              <label className="field">
                <span className="field-label">Station</span>
                <input value={draft.station ?? ''} onChange={(e) => setDraft({ ...draft, station: e.target.value })} />
              </label>
              <label className="field">
                <span className="field-label">Year</span>
                <input
                  type="number"
                  value={draft.year ?? ''}
                  onChange={(e) => setDraft({ ...draft, year: e.target.value ? Number(e.target.value) : undefined })}
                />
              </label>
              <label className="field">
                <span className="field-label">Author</span>
                <input value={draft.author ?? ''} onChange={(e) => setDraft({ ...draft, author: e.target.value })} />
              </label>
              <label className="field">
                <span className="field-label">Keywords</span>
                <input value={draft.keywords ?? ''} onChange={(e) => setDraft({ ...draft, keywords: e.target.value })} />
              </label>
              <label className="field">
                <span className="field-label">Attribution</span>
                <input value={draft.attribution ?? ''} onChange={(e) => setDraft({ ...draft, attribution: e.target.value })} />
              </label>
              <label className="field">
                <span className="field-label">Source</span>
                <input value={draft.source ?? ''} onChange={(e) => setDraft({ ...draft, source: e.target.value })} />
              </label>
              <div className="form-actions">
                <button className="btn primary" onClick={save} disabled={busy || !draft.title?.trim()}>
                  {busy ? 'Saving…' : 'Save changes'}
                </button>
              </div>
            </div>
          ) : (
            <dl className="meta-list">
              <MetaRow label="Description" value={asset.description} />
              <MetaRow label="Topic" value={asset.topic} />
              <MetaRow label="Expedition" value={asset.expedition} />
              <MetaRow label="Station" value={asset.station} />
              <MetaRow label="Year" value={asset.year} />
              <MetaRow label="Author" value={asset.author} />
              <MetaRow label="Keywords" value={asset.keywords} />
              <MetaRow label="Attribution" value={asset.attribution} />
              <MetaRow label="Source" value={asset.source} />
              <MetaRow label="Created" value={formatDate(asset.created_at)} />
              <MetaRow label="Updated" value={formatDate(asset.updated_at)} />
            </dl>
          )}
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Versions</h2>
            <span className="muted small">Originals are never overwritten (BR-10)</span>
          </div>

          <ul className="version-list">
            {versions.map((version) => (
              <li key={version.id}>
                <div className="version-top">
                  <strong>v{version.version_number}</strong>
                  <span className={`status status-${version.processing_status.toLowerCase()}`}>
                    {version.processing_status}
                  </span>
                </div>
                <div className="version-name">{version.original_filename}</div>
                <dl className="version-meta">
                  <div>
                    <dt>Size</dt>
                    <dd>{formatBytes(version.size_bytes)}</dd>
                  </div>
                  <div>
                    <dt>Hash</dt>
                    <dd title={version.file_hash}>{shortHash(version.file_hash)}</dd>
                  </div>
                  {version.page_count != null && (
                    <div>
                      <dt>Pages</dt>
                      <dd>{version.page_count}</dd>
                    </div>
                  )}
                  <div>
                    <dt>Evidence</dt>
                    <dd>{version.passage_count}</dd>
                  </div>
                  <div>
                    <dt>Uploaded</dt>
                    <dd>{formatDate(version.uploaded_at)}</dd>
                  </div>
                </dl>
                {version.processing_note && (
                  <p className="version-note">{version.processing_note}</p>
                )}
                {version.note && <p className="version-note">“{version.note}”</p>}
                {version.processing_error && (
                  <p className="version-error">{version.processing_error}</p>
                )}
                <a className="btn small" href={api.downloadUrl(asset.id, version.id)}>
                  Download original
                </a>
              </li>
            ))}
          </ul>

          <div className="version-upload">
            <label className="field">
              <span className="field-label">New version note</span>
              <input
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="e.g. corrected figure 2"
              />
            </label>
            <input
              ref={fileRef}
              type="file"
              hidden
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void addVersion(file)
              }}
            />
            <button className="btn" disabled={busy} onClick={() => fileRef.current?.click()}>
              {busy ? 'Uploading…' : 'Upload new version'}
            </button>
          </div>
        </section>
      </div>

      <EvidencePanel
        assetId={asset.id}
        versions={versions}
        onChange={load}
        initialVersionId={targetVersionId}
        highlightId={targetPassageId}
      />
    </div>
  )
}
