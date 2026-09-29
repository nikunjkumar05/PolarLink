from __future__ import annotations

import logging

from sqlalchemy import select

from ..db import SessionLocal
from ..models import AssetVersion

log = logging.getLogger(__name__)

TERMINAL_STATUSES = ("DONE", "FAILED")


def process_version(version_id: int) -> None:
    """FR-06 placeholder — records the outcome for a newly stored version.

    Text extraction itself lands with the document-processing module; until then
    the version is marked DONE so the repository flow stays usable end to end.
    """
    db = SessionLocal()
    try:
        version = db.get(AssetVersion, version_id)
        if version is None:
            return
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
