from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..models import EvidencePassage
from .embeddings import get_provider, provider_error, to_blob

log = logging.getLogger(__name__)


@dataclass(slots=True)
class IndexStats:
    keyword_ready: bool
    keyword_rows: int
    total_passages: int
    embedded_passages: int
    embedding_model: str | None
    embedding_ready: bool
    embedding_error: str | None


def clear_version(db: Session, version_id: int) -> None:
    """Drop a version's keyword rows before its passages are rebuilt."""
    db.execute(
        text(
            "DELETE FROM passage_fts WHERE CAST(asset_version_id AS INTEGER) = :version_id"
        ),
        {"version_id": version_id},
    )


def index_passages(db: Session, passages: list[EvidencePassage]) -> str | None:
    """Persist FR-10 keyword rows and FR-11 embeddings for fresh passages.

    Returns a human-readable note when the semantic index could not be built;
    the keyword index and the passages themselves are unaffected either way.
    """
    if not passages:
        return None

    note: str | None = None
    provider = get_provider()
    vectors: list = [None] * len(passages)

    if provider is None:
        note = f"Semantic index skipped: {provider_error()}"
        log.warning(note)
    else:
        try:
            vectors = provider.embed([passage.content for passage in passages])
        except Exception as exc:  # noqa: BLE001 - a bad batch must not fail ingestion
            note = f"Semantic index skipped: {type(exc).__name__}: {exc}"
            log.exception("embedding failed; continuing with keyword index only")
            vectors = [None] * len(passages)

    for passage, vector in zip(passages, vectors):
        if vector is None:
            passage.embedding = None
            passage.embedding_model = None
        else:
            passage.embedding = to_blob(vector)
            passage.embedding_model = provider.name

    db.flush()

    db.execute(
        text(
            "INSERT INTO passage_fts (passage_id, asset_id, asset_version_id, content) "
            "VALUES (:passage_id, :asset_id, :asset_version_id, :content)"
        ),
        [
            {
                "passage_id": passage.id,
                "asset_id": passage.asset_id,
                "asset_version_id": passage.asset_version_id,
                "content": passage.content,
            }
            for passage in passages
        ],
    )
    db.flush()
    return note


def stats(db: Session) -> IndexStats:
    total = db.scalar(select(func.count(EvidencePassage.id))) or 0
    embedded = (
        db.scalar(
            select(func.count(EvidencePassage.id)).where(EvidencePassage.embedding.is_not(None))
        )
        or 0
    )
    model = db.scalar(
        select(EvidencePassage.embedding_model)
        .where(EvidencePassage.embedding_model.is_not(None))
        .limit(1)
    )
    try:
        keyword_rows = db.scalar(text("SELECT count(*) FROM passage_fts")) or 0
    except Exception:  # noqa: BLE001 - index table may not exist yet
        keyword_rows = 0

    return IndexStats(
        keyword_ready=keyword_rows > 0,
        keyword_rows=int(keyword_rows),
        total_passages=int(total),
        embedded_passages=int(embedded),
        embedding_model=model,
        embedding_ready=int(embedded) > 0,
        embedding_error=provider_error(),
    )


__all__ = ["IndexStats", "clear_version", "index_passages", "stats"]
