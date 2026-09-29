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

Working prototype. **Modules 1–3** of the requirements document are implemented
and covered by end-to-end tests.

| Acceptance criterion | Status |
| --- | --- |
| AC-01 An authorized user can upload a PDF | done |
| AC-02 The PDF becomes searchable | done |
| AC-03 A query retrieves the relevant passage | done |
| AC-04 The search result identifies the correct page | done |
| AC-05 Selecting the result opens the supporting source | done |
| AC-06 … AC-22 generation, review, source-update detection | not built |

Not implemented yet: authentication and RBAC (FR-01/02), image/video/dataset
depth (FR-07–09), outreach generation (FR-15–18), claim–evidence mapping and
review (FR-19–25), publication (FR-26–28), source-change detection (FR-31–43).

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

---

## Project structure

```
PolarLink/
├── backend/
│   ├── app/
│   │   ├── api/            # assets, evidence, search routers
│   │   ├── models/         # Asset, AssetVersion, EvidencePassage
│   │   ├── schemas/        # pydantic request/response models
│   │   ├── services/       # storage, extract, processing, embeddings, index, search
│   │   ├── config.py       # paths, limits, allowed values
│   │   ├── db.py           # engine, session, FK enforcement
│   │   ├── migrations.py   # schema self-repair for SQLite
│   │   └── main.py         # app, CORS, lifespan
│   ├── scripts/
│   │   ├── seed.py         # corpus upload through the real API
│   │   └── demo.py         # reset + seed + warm index + sample PDF
│   ├── requirements.txt
│   └── data/ storage/      # created at runtime (gitignored)
├── frontend/
│   └── src/
│       ├── pages/          # Landing, Repository, Upload, AssetDetail, EvidencePanel, Search
│       ├── api/client.ts   # typed fetch client
│       ├── types.ts        # shared API types
│       └── index.css       # design tokens + components
├── e2e/                    # end-to-end suites (13 + 28 + 51 checks)
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
.venv\Scripts\python ..\e2e\module3_search.py       # 51 checks — hybrid search and deep links
```

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
| FR-01, FR-02 | authentication, RBAC | not built |
| FR-07, FR-08 | image management, video transcripts | not built |
| FR-15 → FR-18 | outreach generation, audience selection, evidence-grounded generation, evidence ID validation | not built |
| FR-19 → FR-25 | claim–evidence mapping, drafts, review workflow | not built |
| FR-26 → FR-28 | publication, published repository, social export | not built |
| FR-31 → FR-43 | source-change detection, impact analysis, re-verification | not built |

The full specification — functional requirements, business rules, acceptance
criteria, use cases and the domain model — is in
`Requirement Engineering and Domain Modeling — SIH26063.md`.
