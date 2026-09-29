from __future__ import annotations

import logging

from sqlalchemy import delete, select

from ..db import SessionLocal
from ..models import AssetVersion, EvidencePassage
from . import extract as extractor
from . import index as indexer
from .storage import resolve_stored

log = logging.getLogger(__name__)

TERMINAL_STATUSES = ("DONE", "FAILED")


def process_version(version_id: int) -> None:
    """FR-06 — extract page-aware text and emit EvidencePassage rows.

    Runs off the request thread (NFR-02). The original file is never modified;
    a failure marks the version FAILED and leaves the upload intact (NFR-03).
    """
    db = SessionLocal()
    try:
        version = db.get(AssetVersion, version_id)
        if version is None:
            return
        version.processing_status = "PROCESSING"
        db.commit()

        path = resolve_stored(version.file_path)
        result = extractor.extract(path, version.mime_type, version.original_filename)
        chunks = extractor.chunk_pages(result.pages)

        # Reprocessing replaces passages; the source version itself is untouched.
        indexer.clear_version(db, version.id)
        db.execute(
            delete(EvidencePassage).where(EvidencePassage.asset_version_id == version.id)
        )
        passages = [
            EvidencePassage(
                asset_version_id=version.id,
                asset_id=version.asset_id,
                sequence_number=index,
                location_type="PAGE" if chunk.page_number else "TEXT",
                content=chunk.text,
                page_number=chunk.page_number,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                char_count=len(chunk.text),
            )
            for index, chunk in enumerate(chunks)
        ]
        db.add_all(passages)
        db.flush()

        # FR-10 keyword index + FR-11 embeddings for the new passages.
        index_note = indexer.index_passages(db, passages)

        version.page_count = max(
            (page.page_number for page in result.pages if page.page_number), default=0
        ) or None
        version.passage_count = len(chunks)
        version.processing_note = " ".join(
            part for part in (result.warning, index_note) if part
        ) or None
        version.processing_status = "DONE"
        version.processing_error = None
        db.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception("processing failed for version %s", version_id)
        db.rollback()
        version = db.get(AssetVersion, version_id)
        if version is not None:
            version.processing_status = "FAILED"
            version.processing_error = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


def has_active_processing(asset_id: int) -> bool:
    db = SessionLocal()
    try:
        row = db.scalars(
            select(AssetVersion.id).where(
                AssetVersion.asset_id == asset_id,
                AssetVersion.processing_status.notin_(TERMINAL_STATUSES),
            )
        ).first()
        return row is not None
    finally:
        db.close()
