from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.asset import AssetSummary
from ..schemas.search import IndexInfo, SearchHit, SearchResponse, SearchVersionRef
from ..services import search as searcher
from ..services.search import MODES, SearchFilters

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query("", description="free-text query"),
    mode: str = Query("hybrid", description="hybrid | keyword | semantic"),
    limit: int = Query(20, ge=1, le=searcher.MAX_LIMIT),
    asset_type: str | None = Query(None),
    expedition: str | None = Query(None),
    station: str | None = Query(None),
    topic: str | None = Query(None),
    year: int | None = Query(None, ge=1800, le=2200),
    access_level: str | None = Query(None),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """FR-10/11/12 — hybrid retrieval over EvidencePassage rows.

    Keyword leg ranks with SQLite FTS5 BM25; the semantic leg ranks by cosine
    similarity against local embeddings. Reciprocal Rank Fusion (k=60) merges
    them so a passage found by only one retriever still surfaces.
    """
    filters = SearchFilters(
        asset_type=asset_type,
        expedition=expedition,
        station=station,
        topic=topic,
        year=year,
        access_level=access_level,
    )
    outcome = searcher.run(db, query=q, mode=mode, filters=filters, limit=limit)
    rows = searcher.load_hits(db, outcome.hits)

    ranked = {hit.passage_id: (index + 1, hit) for index, hit in enumerate(outcome.hits)}
    items: list[SearchHit] = []
    for passage, asset, version in rows:
        rank, hit = ranked[passage.id]
        items.append(
            SearchHit(
                rank=rank,
                score=round(hit.score, 6),
                sources=hit.sources,
                keyword_rank=hit.keyword_rank,
                semantic_rank=hit.semantic_rank,
                keyword_score=hit.keyword_score,
                semantic_score=hit.semantic_score,
                passage=passage,
                asset=AssetSummary.model_validate(asset),
                version=SearchVersionRef(id=version.id, version_number=version.version_number),
            )
        )
    items.sort(key=lambda item: item.rank)

    return SearchResponse(
        query=outcome.query,
        mode=outcome.mode,
        took_ms=outcome.took_ms,
        total=outcome.total,
        limit=limit,
        items=items,
        index=IndexInfo.model_validate(outcome.index),
        note=outcome.note,
    )


@router.get("/modes", response_model=list[str])
def list_modes() -> list[str]:
    return list(MODES)
