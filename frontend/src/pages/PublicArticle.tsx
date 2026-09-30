import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api, ApiError } from '../api/client'
import { formatDate } from '../lib/format'
import type { Claim } from '../types'

interface PublicPayload {
  title: string
  summary: string | null
  body: string
  author_name: string | null
  published_at: string | null
  audience: string | null
  claims: Claim[]
}

/** FR-27 — the reader-facing article, no workflow chrome. */
export default function PublicArticle() {
  const { slug } = useParams()
  const [data, setData] = useState<PublicPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .publicArticle(String(slug))
      .then((value) => setData(value as unknown as PublicPayload))
      .catch((err) => setError(err instanceof ApiError ? err.message : 'article not found'))
  }, [slug])

  if (error) {
    return (
      <div className="page narrow">
        <p className="error-box">{error}</p>
        <Link className="link" to="/articles">Back to articles</Link>
      </div>
    )
  }
  if (!data) return <div className="page narrow"><p className="muted">Loading…</p></div>

  return (
    <article className="page narrow reader">
      <p className="crumb">
        <Link className="link" to="/">PolarLink</Link> / published article
      </p>
      <h1>{data.title}</h1>
      <p className="small muted">
        {data.author_name ?? 'PolarLink'} · {formatDate(data.published_at)}
        {data.audience ? ` · for ${data.audience}` : ''}
      </p>
      {data.summary && <p className="lede">{data.summary}</p>}

      <div className="body-preview">
        {data.body.split('\n\n').map((paragraph, index) => (
          <p key={index}>{paragraph.replace(/^#\s*/, '')}</p>
        ))}
      </div>

      <section className="panel sources">
        <h2>Sources</h2>
        <p className="small muted">
          Every statement above was written from these archived passages.
        </p>
        {data.claims.map((claim) => (
          <div key={claim.id} className="evidence-block">
            <p className="claim-text">{claim.text}</p>
            {claim.evidence_links.map((link) =>
              link.evidence ? (
                <div key={link.id} className="evidence-row">
                  <div className="evidence-meta">
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
                  </div>
                  <p className="excerpt">{link.evidence.excerpt}</p>
                </div>
              ) : null,
            )}
          </div>
        ))}
      </section>
    </article>
  )
}