import { useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { AccessLevel, AssetPayload, AssetType } from '../types'
import { formatBytes } from '../lib/format'

const ASSET_TYPES: AssetType[] = ['PDF', 'IMAGE', 'VIDEO', 'DATASET', 'ACTIVITY', 'OTHER']
const ACCESS_LEVELS: AccessLevel[] = ['PUBLIC', 'INTERNAL', 'RESTRICTED']

const EMPTY: AssetPayload = {
  title: '',
  description: '',
  asset_type: 'PDF',
  topic: '',
  expedition: '',
  station: '',
  year: undefined,
  author: '',
  keywords: '',
  attribution: '',
  source: '',
  access_level: 'PUBLIC',
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <small className="muted">{hint}</small>}
    </label>
  )
}

export default function Upload() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [form, setForm] = useState<AssetPayload>(EMPTY)
  const [dragging, setDragging] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = <K extends keyof AssetPayload>(key: K, value: AssetPayload[K]) =>
    setForm((current) => ({ ...current, [key]: value }))

  const chooseFile = (next: File | null) => {
    if (!next) return
    setFile(next)
    setError(null)
    if (!form.title.trim()) {
      const base = next.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim()
      set('title', base.charAt(0).toUpperCase() + base.slice(1))
    }
    const ext = next.name.split('.').pop()?.toLowerCase() ?? ''
    const guesses: Record<string, AssetType> = {
      pdf: 'PDF',
      png: 'IMAGE',
      jpg: 'IMAGE',
      jpeg: 'IMAGE',
      gif: 'IMAGE',
      webp: 'IMAGE',
      mp4: 'VIDEO',
      mov: 'VIDEO',
      csv: 'DATASET',
      json: 'DATASET',
      xlsx: 'DATASET',
    }
    const guess = guesses[ext]
    if (guess && form.asset_type === 'PDF') set('asset_type', guess)
  }

  const valid = useMemo(() => Boolean(file && form.title.trim()), [file, form.title])

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!file || !valid) return
    setSubmitting(true)
    setError(null)
    try {
      const asset = await api.createAsset(file, form)
      navigate(`/assets/${asset.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
      setSubmitting(false)
    }
  }

  return (
    <div className="narrow">
      <div className="page-head">
        <div>
          <h1>Upload asset</h1>
          <p className="muted">
            Stores the original file as an immutable AssetVersion and records descriptive metadata
            (FR-03, FR-04).
          </p>
        </div>
        <Link className="btn" to="/">
          Back to repository
        </Link>
      </div>

      <form className="panel" onSubmit={submit}>
        <div
          className={dragging ? 'dropzone dragging' : 'dropzone'}
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            chooseFile(event.dataTransfer.files?.[0] ?? null)
          }}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click()
          }}
        >
          <input
            ref={inputRef}
            type="file"
            hidden
            onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
          />
          {file ? (
            <div className="dropzone-file">
              <strong>{file.name}</strong>
              <span className="muted">{formatBytes(file.size)}</span>
              <button
                type="button"
                className="link"
                onClick={(event) => {
                  event.stopPropagation()
                  setFile(null)
                  if (inputRef.current) inputRef.current.value = ''
                }}
              >
                Remove
              </button>
            </div>
          ) : (
            <>
              <strong>Drop a file here or click to browse</strong>
              <span className="muted">PDF, images, video, datasets — original is preserved</span>
            </>
          )}
        </div>

        <div className="form-grid">
          <Field label="Title" hint="Required">
            <input
              value={form.title ?? ''}
              onChange={(event) => set('title', event.target.value)}
              placeholder="42nd Indian Antarctic Expedition Report"
              required
            />
          </Field>

          <Field label="Asset type">
            <select
              value={form.asset_type}
              onChange={(event) => set('asset_type', event.target.value as AssetType)}
            >
              {ASSET_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Description" hint="Shown in repository cards">
            <textarea
              rows={3}
              value={form.description ?? ''}
              onChange={(event) => set('description', event.target.value)}
            />
          </Field>

          <Field label="Topic">
            <input
              value={form.topic ?? ''}
              onChange={(event) => set('topic', event.target.value)}
              placeholder="Antarctica"
            />
          </Field>

          <Field label="Expedition">
            <input
              value={form.expedition ?? ''}
              onChange={(event) => set('expedition', event.target.value)}
              placeholder="IAE-42"
            />
          </Field>

          <Field label="Station">
            <input
              value={form.station ?? ''}
              onChange={(event) => set('station', event.target.value)}
              placeholder="Maitri"
            />
          </Field>

          <Field label="Year">
            <input
              type="number"
              min={1800}
              max={2200}
              value={form.year ?? ''}
              onChange={(event) =>
                set('year', event.target.value ? Number(event.target.value) : undefined)
              }
              placeholder="2025"
            />
          </Field>

          <Field label="Author / contributor">
            <input
              value={form.author ?? ''}
              onChange={(event) => set('author', event.target.value)}
              placeholder="NCPOR"
            />
          </Field>

          <Field label="Keywords" hint="Comma separated">
            <input
              value={form.keywords ?? ''}
              onChange={(event) => set('keywords', event.target.value)}
              placeholder="sea ice, expedition, climate"
            />
          </Field>

          <Field label="Attribution">
            <input
              value={form.attribution ?? ''}
              onChange={(event) => set('attribution', event.target.value)}
              placeholder="© NCPOR, MoES"
            />
          </Field>

          <Field label="Source" hint="Original URL or reference">
            <input
              value={form.source ?? ''}
              onChange={(event) => set('source', event.target.value)}
              placeholder="https://ncpor.res.in/…"
            />
          </Field>

          <Field label="Access level">
            <select
              value={form.access_level}
              onChange={(event) => set('access_level', event.target.value as AccessLevel)}
            >
              {ACCESS_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Version note" hint="Optional reason for this upload">
            <input
              value={form.note ?? ''}
              onChange={(event) => set('note', event.target.value)}
              placeholder="Initial submission"
            />
          </Field>
        </div>

        {error && <div className="banner error">{error}</div>}

        <div className="form-actions">
          <Link className="btn" to="/">
            Cancel
          </Link>
          <button className="btn primary" type="submit" disabled={!valid || submitting}>
            {submitting ? 'Uploading…' : 'Upload asset'}
          </button>
        </div>
      </form>
    </div>
  )
}
