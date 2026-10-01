# PolarLink

**Evidence-linked knowledge and outreach platform for polar science**
SIH26063 · National Centre for Polar and Ocean Research (NCPOR)

PolarLink turns expedition reports, datasets and photographs into a searchable,
citable knowledge base. Ask a plain-language question and you get back the exact
passage that answers it — with its page number and a link that opens the source
document at that evidence.

The differentiator is not search, it is **traceability**: every result carries an
evidence ID (`E1`, `E2`, …) pointing at a page-aware passage of a real, versioned
file. Nothing is answerable without a source.

---

## Status

Working prototype. **Modules 1–3** (ingest → process → retrieve) plus **modules 4–5**
(claims, review, publication, and source-change impact) are implemented and covered
by end-to-end tests.

| Acceptance criterion | Status |
| --- | --- |
| AC-01 An authorized user can upload a PDF | done |
| AC-02 The PDF becomes searchable | done |
| AC-03 A query retrieves the relevant passage | done |
| AC-04 The search result identifies the correct page | done |
| AC-05 Selecting the result opens the supporting source | done |
| AC-06 … AC-12 claim–evidence mapping, review workflow | done |
| AC-13 … AC-17 publication and public rendering | done |
| AC-18 … AC-22 source-change detection and re-verification | done |

The full loop runs end to end:

```
upload report → search evidence → claim → generate article → reviewer checks
source → publish → upload the changed report → "Affected publication —
re-verification required" → reviewer re-verifies the claim
```

Not implemented yet: image/video/dataset depth (FR-07–09), OCR for scanned PDFs,
social-media export (FR-28b), and scheduled source polling — a source change is
detected when a new version is uploaded, not by a background watcher.

---

## Quick start

**Prerequisites:** Python 3.12+, Node 24+.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- API: <http://127.0.0.1:8000>
- Interactive docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open **<http://localhost:5173>**. Vite binds the IPv6 loopback, so use
`localhost` — `127.0.0.1:5173` will not connect. `/api` is proxied to port 8000.

### 3. Seed the demo corpus

```powershell
cd backend
.venv\Scripts\python scripts\demo.py --reset
```

Creates seven documents (12 evidence passages, all embedded locally), writes
`demo/sample-upload.pdf` for the upload half of a walkthrough, and runs one
hybrid search so the embedding model is warm — the first query during a demo
does not stall on a cold start.

Without `--reset` the script only tops up missing documents.

---

## Deployment (Docker)

One compose stack: nginx serves the built SPA and reverse-proxies `/api` to the
FastAPI container. Everything runs on a single node — SQLite, the uploaded-file
volume and the ONNX embedding model are all local.

**Prerequisites:** Docker with Compose v2.

```powershell
copy .env.example .env
# put a real key in POLARLINK_JWT_SECRET (see .env.example for generators)

docker compose up -d --build
```

Open **<http://localhost:8080>**. The `seed` service runs once after the API is
healthy and loads the seven-document corpus; it is idempotent, so later `up`
runs only top up missing documents.

| Service | Purpose |
| --- | --- |
| `web` | nginx on `${POLARLINK_PORT:-8080}` — SPA + `/api` proxy + `client_max_body_size 210m` |
| `api` | uvicorn, one worker (SQLite), internal port 8000 only |
| `seed` | one-shot `scripts/demo.py` against the API, exits 0 |

### Notes

- **The embedding model is baked into the image** (`FASTEMBED_CACHE_PATH`), so
  the first search does not download anything and the stack works behind a
  firewall. Rebuilds only re-fetch it if the base image or requirements change.
- **Data survives restarts** in the `polarlink-data` and `polarlink-storage`
  volumes. `docker compose down -v` deletes the database and the stored files.
- **Workers stay at 1** — background processing writes to SQLite and is not
  designed for multiple processes.
- **Logs:** `docker compose logs -f api`, `docker compose logs -f seed`.
- **Restart / stop:** `docker compose restart api`, `docker compose down`.
- **Take it offline:** the API and SPA need no outbound network at runtime; only
  `docker compose build` does.
- **Drop the seeding:** delete the `seed` service from `docker-compose.yml`, or
  simply `docker compose run --rm seed` when you want the corpus back.
- The demo accounts (`admin@ncpor.in` / `admin123`, …) are seeded by that
  service — change or remove them before exposing the stack publicly.

### Behind a reverse proxy / TLS

nginx here listens on HTTP. Terminate TLS in front of it (a cloud load
balancer, or a host nginx/caddy on 443 proxying to `localhost:8080`), then set
`POLARLINK_CORS_ORIGINS` only if the SPA will be served from a different origin
than the API. Same-origin behind this stack needs no CORS at all.

---

## Demo walkthrough

Each beat maps to an acceptance criterion.

| # | Do this | Shows |
| --- | --- | --- |
| 1 | Open `http://localhost:5173` | problem, pipeline, live stats and a real ranked hit |
| 2 | Upload → drag in `demo\sample-upload.pdf` → fill the form | file stored, hashed, `PENDING → DONE`, passages counted (AC-01) |
| 3 | Search → type `anemometer` | the new document ranks #1 with `keyword` + `semantic` chips (AC-02, AC-03) |
| 4 | Read the hit footer | `v1 · p.1 · E13` — page number and evidence ID (AC-04) |
| 5 | Click **Open evidence** | asset page opens with that passage expanded and scrolled into view (AC-05) |
| 6 | Toggle Hybrid / Keyword / Semantic | fusion vs BM25 vs embeddings on the same query |

### The full loop (modules 4–5)

Sign in first — one click on `/login` fills the form. Editors write, reviewers sign off.

| # | Do this | Shows |
| --- | --- | --- |
| 7 | Search → **Claim this passage** on any hit → write the claim | a claim anchored to `v1 · p.1 · E13`; the API refuses a claim with no evidence |
| 8 | **Articles** → tick the claims → **Generate draft** | an article composed only from cited passages (FR-17, FR-20) |
| 9 | Open it → **Submit for review**, sign out, sign in as reviewer → **Approve** → **Publish** | role-gated workflow; an editor cannot approve (403) and DRAFT cannot skip to PUBLISHED (409) |
| 10 | Copy the article's public link from **Open public page** | the reader-facing view with a Sources section |
| 11 | **Upload** a new version of a source that a claim cites | v2 is immutable; the edited passage is detected automatically |
| 12 | **Alerts** → read the before/after diff → pick the passage that still supports it → **Re-verify** | "re-verification required" on the article; claim goes STALE → VERIFIED |

The whole chain is enforced server-side, so it survives being poked in Swagger UI at
`http://localhost:8000/docs`.

---

## How it works

```
PDF
 ↓  text extraction (pypdf), page by page
page-aware evidence passages  (keep page number, offsets, char count)
 ↓
FTS5 keyword rows  +  384-dimension local embedding (BAAI/bge-small-en-v1.5)
 ↓
question → keyword rank ∥ semantic rank → reciprocal-rank fusion (k = 60)
 ↓
passage + page number + evidence ID → link to the original document
```

- **Storage** — SQLite at `backend/data/polarlink.db`; files under
  `backend/storage/assets/<id>/v<n>/`. Originals are never overwritten
  (BR-10): a new upload creates a new version.
- **Search** — `passage_fts` (FTS5, BM25) plus an `embedding` BLOB column on
  `evidence_passages`. Both legs are fused with reciprocal-rank fusion, so a
  passage found by only one retriever still surfaces.
- **Embeddings** — `fastembed` (ONNX, no torch), loaded lazily and cached on
  disk. If the model cannot load, search degrades to keyword-only instead of
  failing; the index bar in the UI reports which legs are live.
- **Integrity** — SQLite foreign keys are enforced, asset deletion cascades and
  clears `passage_fts`, and startup self-repair re-syncs keyword rows and
  missing embeddings.
- **Claims** — a claim cannot be created without at least one evidence passage
  (`POST /api/claims` returns 422 otherwise). Articles are assembled from claims,
  never from free text.
- **Change impact** — when a version above v1 finishes processing, its passages
  are aligned against the previous version's (positional, with token-overlap
  fallback). If a claim cited a passage that changed, the claim goes `STALE`, the
  article is flagged `needs_reverification`, and an `ImpactAlert` records the old
  quote, the new quote, and the page — so a reviewer can compare without opening
  the old file.

---

## API

All endpoints are under `/api`.

### Assets

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/assets` | list with facets, full-text title/keyword filter, paging |
| `POST` | `/assets` | create asset + first version (multipart file + JSON meta) |
| `GET` | `/assets/filters` | facet values for the filter sidebar |
| `GET` | `/assets/{id}` | detail with all versions |
| `PATCH` | `/assets/{id}` | update metadata |
| `DELETE` | `/assets/{id}` | remove asset, versions, passages and index rows |
| `POST` | `/assets/{id}/versions` | upload a new immutable version |
| `GET` | `/assets/{id}/versions/{vid}/download` | original file |

### Evidence

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/versions/{vid}/passages` | passages, optional `q` and `page_number` |
| `GET` | `/versions/{vid}/passages/{pid}` | one passage |
| `GET` | `/versions/{vid}/pages` | page numbers present in the version |
| `POST` | `/versions/{vid}/reprocess` | re-run extraction and re-index |

### Search

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/search?q=&mode=&limit=` | `mode` = `hybrid` \| `keyword` \| `semantic`, plus facet filters; returns hits, per-leg ranks and live index stats |
| `GET` | `/search/modes` | available modes |

### Identity

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/login` | exchange credentials for a JWT |
| `POST` | `/auth/register` | create an account (first one becomes ADMIN) |
| `GET` | `/auth/me` | current user from the bearer token |
| `GET` | `/auth/directory` | accounts, for the sign-in screen |

### Claims

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/claims?status=&topic=&q=` | claim library |
| `POST` | `/claims` | create a claim; `evidence` is required (422 without it) |
| `PATCH` | `/claims/{id}` | edit the wording |
| `POST` | `/claims/{id}/status?status=` | reviewer accepts or disputes (REVIEWER only) |
| `DELETE` | `/claims/{id}` | remove an unused claim |
| `GET` | `/claims/{id}/events` | its audit trail |

### Articles

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/articles?status=` | list with open-alert counts |
| `POST` | `/articles` | assemble from `claim_ids` and render the body |
| `POST` | `/articles/{id}/generate?mode=auto\|extractive\|llm` | re-render the draft |
| `POST` | `/articles/{id}/transition?target=` | `IN_REVIEW`, `APPROVED`, `PUBLISHED`, `REJECTED`, `DRAFT` |
| `GET` | `/articles/{id}/events` | audit trail: who did what, in order |
| `GET` | `/articles/by-slug/{slug}` | public reader view, published articles only |
| `DELETE` | `/articles/{id}` | remove the article, claims survive |
| `GET` | `/capabilities` | whether LLM drafting is configured |

### Source-change impact

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/alerts?status=OPEN` | re-verification inbox |
| `GET` | `/alerts/{id}` | one alert with both quotes |
| `GET` | `/alerts/{id}/passages` | passages in the new version, for re-anchoring |
| `POST` | `/alerts/{id}/resolve` | `REVERIFIED` (optionally re-link the passage) or `ACKNOWLEDGED` |
| `GET` | `/alerts/asset/{id}/changes` | diff the two newest versions |

### Health

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | liveness + loaded modules |

---

## Frontend routes

| Route | Page |
| --- | --- |
| `/` | landing page: problem, pipeline, live stats, AC checklist |
| `/repository` | faceted asset grid |
| `/upload` | drag-and-drop upload with metadata form |
| `/assets/:id` | metadata, immutable version history, evidence passages (FR-14 deep link: `?v=&passage=`) |
| `/search` | hybrid search with mode switch, facets and evidence deep links (`?q=` pre-fills the query) |
| `/login` | sign in; one click fills the seeded demo accounts |
| `/claims` | claim library with evidence and reviewer actions |
| `/articles` | list + article builder (pick claims → generate) |
| `/articles/:id` | draft, workflow controls, claims-with-evidence, audit trail |
| `/alerts` | re-verification inbox with a before/after source diff |
| `/read/:slug` | the published article as a reader sees it |

---

## Project structure

```
PolarLink/
├── backend/
│   ├── Dockerfile         # production API image
│   ├── app/
│   │   ├── api/            # assets, evidence, search, auth, claims, articles, alerts
│   │   ├── models/         # Asset, AssetVersion, EvidencePassage, Claim, Article, ImpactAlert, User
│   │   ├── schemas/        # pydantic request/response models
│   │   ├── services/       # storage, extract, processing, embeddings, index, search,
│   │   │                   # auth, authoring, diffing, editorial
│   │   ├── config.py       # paths, limits, allowed values
│   │   ├── db.py           # engine, session, FK enforcement
│   │   ├── migrations.py   # schema self-repair for SQLite
│   │   └── main.py         # app, CORS, lifespan
│   ├── scripts/
│   │   ├── seed.py         # corpus + demo users, uploaded through the real API
│   │   ├── demo.py         # reset + seed + warm index + sample PDF
│   │   └── smoke_editorial.py  # 40 checks — claims, workflow, impact, re-verification
│   ├── requirements.txt
│   └── data/ storage/      # created at runtime (gitignored)
├── frontend/
│   ├── Dockerfile         # vite build → nginx
│   └── src/
│       ├── pages/          # Landing, Repository, Upload, AssetDetail, EvidencePanel,
│       │                   # Search, Login, Claims, Articles, ArticleDetail, Alerts, PublicArticle
│       ├── api/client.ts   # typed fetch client + bearer token
│       ├── lib/useAuth.ts  # session + role helpers
│       ├── types.ts        # shared API types
│       └── index.css       # design tokens + components
├── e2e/                    # end-to-end suites (13 + 28 + 52 checks)
├── deploy/nginx.conf       # SPA fallback + /api reverse proxy
├── docker-compose.yml      # web + api + one-shot seed
├── .env.example            # copy to .env — set POLARLINK_JWT_SECRET
├── demo/sample-upload.pdf  # fresh document for the upload beat
├── Requirement Engineering and Domain Modeling — SIH26063.md
├── SIH26063_Novelty_and_Differentiation_Document.docx
├── flowchart.md
└── plan.txt
```

---

## Tests

Both servers must be running; the suites talk to the frontend proxy on port 5173.

```powershell
cd backend
.venv\Scripts\python ..\e2e\module1_repository.py   # 13 checks — repository and upload
.venv\Scripts\python ..\e2e\module2_processing.py   # 28 checks — extraction and passages
.venv\Scripts\python ..\e2e\module3_search.py       # 52 checks — hybrid search and deep links
.venv\Scripts\python scripts\smoke_editorial.py     # 40 checks — claims, workflow, impact
```

Module 1–2 leave assets behind; run `scripts\demo.py --reset` afterwards to get
back to a clean 7-document corpus. The editorial suite deletes what it creates.

Frontend checks:

```powershell
cd frontend
npm run lint      # oxlint — zero warnings expected
npm run build     # tsc -b && vite build
```

---

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `POLARLINK_DATA_DIR` | `backend/data` | SQLite database location |
| `POLARLINK_STORAGE_DIR` | `backend/storage` | uploaded file storage |
| `POLARLINK_DATABASE_URL` | `sqlite:///backend/data/polarlink.db` | any SQLAlchemy URL (Postgres when scaling) |
| `POLARLINK_JWT_SECRET` | `polarlink-dev-secret-change-me` | token signing key — **set this in any real deployment** |
| `POLARLINK_JWT_TTL` | `43200` | session lifetime in seconds |
| `POLARLINK_CORS_ORIGINS` | unset | extra comma-separated origins allowed to call the API cross-origin |
| `POLARLINK_LLM_KEY` | unset | enables LLM drafting; without it articles are composed extractively |
| `POLARLINK_LLM_BASE_URL` | `https://api.openai.com/v1` | any OpenAI-compatible endpoint |
| `POLARLINK_LLM_MODEL` | `gpt-4o-mini` | model id used for drafting |

### Demo accounts

Seeded by `demo.py` / `seed.py`; passwords are `<role lowercase>123`.

| Email | Role |
| --- | --- |
| `admin@ncpor.in` | ADMIN |
| `editor@ncpor.in` | EDITOR |
| `reviewer@ncpor.in` | REVIEWER |

### Drafting modes

Without `POLARLINK_LLM_KEY`, an article body is composed **extractively**: each
paragraph is a sentence taken from a cited passage, so the draft cannot state
anything the archive does not already say. Set the key and the same claim set is
sent to an LLM for prose, with citation markers checked against the input; if the
model is unreachable or returns too little, it falls back to extractive.

Uploads are capped at 200 MB (`MAX_UPLOAD_BYTES`). Allowed asset types:
`PDF`, `IMAGE`, `VIDEO`, `DATASET`, `ACTIVITY`, `OTHER`. Access levels:
`PUBLIC`, `INTERNAL`, `RESTRICTED`.

---

## Requirements coverage

| Group | Requirement | State |
| --- | --- | --- |
| FR-03 → FR-06 | upload, metadata, classification, processing | implemented |
| FR-09 | dataset/CSV handling (text) | implemented |
| FR-10 → FR-14 | keyword, semantic, hybrid, filtering, evidence-level retrieval, source navigation | implemented |
| FR-01, FR-02 | authentication, roles (ADMIN / EDITOR / REVIEWER) | implemented (JWT + PBKDF2) |
| FR-07, FR-08 | image management, video transcripts | not built |
| FR-15 → FR-18 | evidence-grounded generation, audience selection | implemented (extractive; LLM optional) |
| FR-19 → FR-25 | claim–evidence mapping, drafts, review workflow, audit trail | implemented |
| FR-26 → FR-27 | publication, public reader view | implemented |
| FR-28 | social-media export | not built |
| FR-31 → FR-43 | source-change detection, impact analysis, re-verification | implemented on upload; no scheduled polling |

The full specification — functional requirements, business rules, acceptance
criteria, use cases and the domain model — is in
`Requirement Engineering and Domain Modeling — SIH26063.md`.
