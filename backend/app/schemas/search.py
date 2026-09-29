from __future__ import annotations

from pydantic import BaseModel

from .asset import AssetSummary
from .evidence import EvidencePassageOut, VersionInfo


class SearchVersionRef(BaseModel):
    id: int
    version_number: int


class SearchHit(BaseModel):
    rank: int
    score: float
    sources: list[str]
    keyword_rank: int | None = None
    semantic_rank: int | None = None
    keyword_score: float | None = None
    semantic_score: float | None = None
    passage: EvidencePassageOut
    asset: AssetSummary
    version: SearchVersionRef


class IndexInfo(BaseModel):
    keyword_ready: bool
    keyword_rows: int
    total_passages: int
    embedded_passages: int
    embedding_model: str | None = None
    embedding_ready: bool
    embedding_error: str | None = None


class SearchResponse(BaseModel):
    query: str
    mode: str
    took_ms: int
    total: int
    limit: int
    items: list[SearchHit]
    index: IndexInfo
    note: str | None = None
