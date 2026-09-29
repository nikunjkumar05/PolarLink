from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import Asset, AssetVersion, EvidencePassage
from .embeddings import get_provider, provider_error

log = logging.getLogger(__name__)

MODES = ("hybrid", "keyword", "semantic")
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
RRF_K = 60
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Keyword search drops function words so "how many fox kits were born" ranks on
# the content terms rather than on "how"/"were". If a query is nothing but
# stopwords we fall back to the raw terms so it never matches nothing.
STOPWORDS = frozenset(
    """
    a about after again against all am an and any are as at be because been before
    being below between both but by can did do does doing down during each few for
    from further had has have having he her here hers herself him himself his how
    i if in into is it its itself just me more most my myself no nor not now of off
    on once only or other our ours ourselves out over own same she should so some
    such than that the their theirs them themselves then there these they this
    those through to too under until up very was we were what when where which while
    who whom why will with you your yours yourself yourselves
    """.split()
)

_KEYWORD_SQL = """
    SELECT passage_fts.passage_id AS passage_id, bm25(passage_fts) AS relevance
    FROM passage_fts
    JOIN evidence_passages p ON p.id = passage_fts.passage_id
    JOIN assets a ON a.id = p.asset_id
    WHERE passage_fts MATCH :q {extra}
    ORDER BY relevance ASC
    LIMIT :limit
"""


@dataclass(slots=True)
class SearchFilters:
    asset_type: str | None = None
    expedition: str | None = None
    station: str | None = None
    topic: str | None = None
    year: int | None = None
    access_level: str | None = None

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.asset_type,
                self.expedition,
                self.station,
                self.topic,
                self.year,
                self.access_level,
            )
        )

    def criteria(self) -> list:
        clauses = []
        if self.asset_type:
            clauses.append(Asset.asset_type == self.asset_type)
        if self.expedition:
            clauses.append(Asset.expedition == self.expedition)
        if self.station:
            clauses.append(Asset.station == self.station)
        if self.topic:
            clauses.append(Asset.topic == self.topic)
        if self.year:
            clauses.append(Asset.year == self.year)
        if self.access_level:
            clauses.append(Asset.access_level == self.access_level)
        return clauses

    def extra_sql(self) -> tuple[str, dict]:
        clauses: list[str] = []
        params: dict = {}
        mapping = (
            ("asset_type", "a.asset_type"),
            ("expedition", "a.expedition"),
            ("station", "a.station"),
            ("topic", "a.topic"),
            ("year", "a.year"),
            ("access_level", "a.access_level"),
        )
        for name, column in mapping:
            value = getattr(self, name)
            if value:
                clauses.append(f"{column} = :{name}")
                params[name] = value
        return (" AND " + " AND ".join(clauses)) if clauses else "", params


@dataclass(slots=True)
class Leg:
    passage_id: int
    rank: int
    score: float


@dataclass(slots=True)
class Hit:
    passage_id: int
    score: float
    sources: list[str] = field(default_factory=list)
    keyword_rank: int | None = None
    semantic_rank: int | None = None
    keyword_score: float | None = None
    semantic_score: float | None = None


@dataclass(slots=True)
class SearchResult:
    query: str
    mode: str
    took_ms: int
    total: int
    hits: list[Hit]
    index: dict
    note: str | None = None


def terms(query: str) -> list[str]:
    return _TOKEN_RE.findall(query or "")


def keyword_terms(query: str) -> list[str]:
    raw = terms(query)
    filtered = [token for token in raw if token.lower() not in STOPWORDS]
    return filtered or raw


def match_query(query: str) -> str:
    """Quote every token so user input can never break FTS5 syntax."""
    return " OR ".join(f'"{token}"' for token in keyword_terms(query))


def _keyword_leg(db: Session, query: str, filters: SearchFilters, limit: int) -> list[Leg]:
    match = match_query(query)
    if not match:
        return []

    extra, filter_params = filters.extra_sql()
    params = {"q": match, "limit": limit, **filter_params}

    try:
        rows = db.execute(text(_KEYWORD_SQL.format(extra=extra)), params).all()
    except Exception:  # noqa: BLE001 - a bad match must degrade, not 500
        log.exception("keyword search failed for %r", query)
        return []

    return [
        Leg(passage_id=int(row.passage_id), rank=index, score=float(row.relevance))
        for index, row in enumerate(rows, start=1)
    ]


def _semantic_leg(db: Session, query: str, filters: SearchFilters, limit: int) -> list[Leg]:
    provider = get_provider()
    if provider is None:
        log.warning("semantic search unavailable: %s", provider_error())
        return []

    statement = (
        select(EvidencePassage.id, EvidencePassage.embedding)
        .join(Asset, Asset.id == EvidencePassage.asset_id)
        .where(EvidencePassage.embedding.is_not(None))
    )
    for clause in filters.criteria():
        statement = statement.where(clause)

    rows = db.execute(statement).all()
    if not rows:
        return []

    try:
        vector = np.asarray(provider.embed([query])[0], dtype=np.float32)
    except Exception:  # noqa: BLE001
        log.exception("query embedding failed for %r", query)
        return []

    query_norm = float(np.linalg.norm(vector))
    if query_norm == 0:
        return []

    matrix = np.stack([np.frombuffer(blob, dtype=np.float32) for _, blob in rows])
    similarity = (matrix @ vector) / (
        np.linalg.norm(matrix, axis=1) * query_norm + np.float32(1e-9)
    )
    order = np.argsort(-similarity)

    legs: list[Leg] = []
    for index in order:
        position = int(index)
        legs.append(
            Leg(
                passage_id=int(rows[position][0]),
                rank=len(legs) + 1,
                score=float(similarity[position]),
            )
        )
        if len(legs) >= limit:
            break
    return legs


def _fuse(legs: dict[str, list[Leg]]) -> list[Hit]:
    fused: dict[int, Hit] = {}
    for source, ranked in legs.items():
        for leg in ranked:
            hit = fused.setdefault(leg.passage_id, Hit(passage_id=leg.passage_id, score=0.0))
            hit.score += 1.0 / (RRF_K + leg.rank)
            hit.sources.append(source)
            if source == "keyword":
                hit.keyword_rank = leg.rank
                hit.keyword_score = leg.score
            else:
                hit.semantic_rank = leg.rank
                hit.semantic_score = leg.score

    return sorted(
        fused.values(),
        key=lambda hit: (
            -hit.score,
            hit.keyword_rank if hit.keyword_rank is not None else MAX_LIMIT,
            hit.passage_id,
        ),
    )


def _index_payload(db: Session) -> dict:
    from .index import stats

    snapshot = stats(db)
    return {
        "keyword_ready": snapshot.keyword_ready,
        "keyword_rows": snapshot.keyword_rows,
        "total_passages": snapshot.total_passages,
        "embedded_passages": snapshot.embedded_passages,
        "embedding_model": snapshot.embedding_model,
        "embedding_ready": snapshot.embedding_ready,
        "embedding_error": snapshot.embedding_error,
    }


def run(
    db: Session,
    query: str,
    mode: str = "hybrid",
    filters: SearchFilters | None = None,
    limit: int = DEFAULT_LIMIT,
) -> SearchResult:
    started = time.perf_counter()
    filters = filters or SearchFilters()
    mode = mode if mode in MODES else "hybrid"
    limit = max(1, min(limit, MAX_LIMIT))
    query = (query or "").strip()

    index_payload = _index_payload(db)
    if not query:
        return SearchResult(
            query=query,
            mode=mode,
            took_ms=0,
            total=0,
            hits=[],
            index=index_payload,
            note="Enter a search term.",
        )

    legs: dict[str, list[Leg]] = {}
    if mode in ("hybrid", "keyword"):
        legs["keyword"] = _keyword_leg(db, query, filters, limit)
    if mode in ("hybrid", "semantic"):
        legs["semantic"] = _semantic_leg(db, query, filters, limit)

    fused = _fuse(legs)
    took_ms = int((time.perf_counter() - started) * 1000)

    note: str | None = None
    keyword_hits = len(legs.get("keyword", []))
    semantic_hits = len(legs.get("semantic", []))
    if mode == "semantic" and get_provider() is None:
        note = f"Semantic search unavailable: {provider_error()}"
    elif mode == "hybrid" and not keyword_hits and not semantic_hits:
        note = "No matches. Try fewer or different terms."
    elif mode == "hybrid" and not semantic_hits and get_provider() is None:
        note = "Keyword-only results: semantic index unavailable."
    elif not fused and mode == "keyword":
        note = "No matches. Try fewer or different terms."

    return SearchResult(
        query=query,
        mode=mode,
        took_ms=took_ms,
        total=len(fused),
        hits=fused[:limit],
        index=index_payload,
        note=note,
    )


def load_hits(db: Session, hits: list[Hit]) -> list[tuple[EvidencePassage, Asset, AssetVersion]]:
    if not hits:
        return []
    statement = (
        select(EvidencePassage, Asset, AssetVersion)
        .join(Asset, Asset.id == EvidencePassage.asset_id)
        .join(AssetVersion, AssetVersion.id == EvidencePassage.asset_version_id)
        .where(EvidencePassage.id.in_([hit.passage_id for hit in hits]))
    )
    rows = db.execute(statement).all()
    order = {hit.passage_id: index for index, hit in enumerate(hits)}
    rows.sort(key=lambda row: order.get(row[0].id, MAX_LIMIT))
    return rows
