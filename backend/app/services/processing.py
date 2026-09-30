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

        # FR-31 / FR-40 — when this is not the first version of the asset, compare
        # it with its predecessor and flag any claim whose evidence just moved.
        # Runs before DONE so a client that waits for DONE also waits for alerts.
        if version.version_number > 1:
            impact_note = assess_impact(db, version.id)
            if impact_note:
                version.processing_note = " ".join(
                    part for part in (version.processing_note, impact_note) if part
                )

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


def _passages_for(db, version_id: int) -> list[EvidencePassage]:
    return list(
        db.scalars(
            select(EvidencePassage)
            .where(EvidencePassage.asset_version_id == version_id)
            .order_by(EvidencePassage.sequence_number)
        ).all()
    )


def assess_impact(db, current_version_id: int) -> str | None:
    """FR-31 — diff this version against the one before it and raise alerts.

    Returns a short note for the version card, or None when nothing that a
    claim depends on changed. Never raises: a failed impact assessment must
    not turn a good upload into a failed one.
    """
    from . import diffing
    from . import editorial

    try:
        current = db.get(AssetVersion, current_version_id)
        if current is None:
            return None

        previous = db.scalar(
            select(AssetVersion)
            .where(
                AssetVersion.asset_id == current.asset_id,
                AssetVersion.version_number < current.version_number,
                AssetVersion.processing_status == "DONE",
            )
            .order_by(AssetVersion.version_number.desc())
            .limit(1)
        )
        if previous is None:
            return None

        diff = diffing.diff_passages(
            _passages_for(db, previous.id), _passages_for(db, current.id)
        )
        asset = current.asset
        alerts = editorial.apply_change(
            db,
            asset=asset,
            previous_version=previous,
            current_version=current,
            diff=diff,
        )
        db.commit()

        if not alerts:
            if diff.changes:
                return (
                    f"Version {current.version_number} differs from version "
                    f"{previous.version_number} ({diff.modified} edited, {diff.added} added, "
                    f"{diff.removed} removed passages); no claim depended on the change."
                )
            return None

        articles = len({alert.article_id for alert in alerts if alert.article_id})
        claims = len({alert.claim_id for alert in alerts})
        return (
            f"Source changed: {claims} claim(s) in {articles} article(s) now need "
            f"re-verification ({len(alerts)} alert(s) raised)."
        )
    except Exception:  # noqa: BLE001
        log.exception("impact assessment failed for version %s", current_version_id)
        db.rollback()
        return None


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
