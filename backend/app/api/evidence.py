from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AssetVersion, EvidencePassage
from ..schemas.evidence import EvidencePassageOut, PassageList, VersionInfo
from ..services import processing

router = APIRouter(prefix="/versions", tags=["evidence"])


def _get_version(db: Session, version_id: int) -> AssetVersion:
    version = db.get(AssetVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="version not found")
    return version


@router.get("/{version_id}/passages", response_model=PassageList)
def list_passages(
    version_id: int,
    q: str | None = Query(None, description="search inside this version's passages"),
    page_number: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> PassageList:
    """FR-13 — evidence-level retrieval scoped to one immutable source version."""
    version = _get_version(db, version_id)

    stmt: Select = select(EvidencePassage).where(
        EvidencePassage.asset_version_id == version_id
    )
    if q and q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(EvidencePassage.content.ilike(needle))
    if page_number is not None:
        stmt = stmt.where(EvidencePassage.page_number == page_number)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(EvidencePassage.sequence_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return PassageList(
        total=total,
        page=page,
        page_size=page_size,
        version=VersionInfo.model_validate(version),
        items=[EvidencePassageOut.model_validate(row) for row in rows],
    )


@router.get("/{version_id}/passages/{passage_id}", response_model=EvidencePassageOut)
def get_passage(
    version_id: int, passage_id: int, db: Session = Depends(get_db)
) -> EvidencePassage:
    passage = db.get(EvidencePassage, passage_id)
    if passage is None or passage.asset_version_id != version_id:
        raise HTTPException(status_code=404, detail="passage not found")
    return passage


@router.get("/{version_id}/pages", response_model=list[int])
def list_pages(version_id: int, db: Session = Depends(get_db)) -> list[int]:
    """Distinct pages that actually have evidence, for page-jump controls."""
    _get_version(db, version_id)
    rows = db.scalars(
        select(EvidencePassage.page_number)
        .where(
            EvidencePassage.asset_version_id == version_id,
            EvidencePassage.page_number.is_not(None),
        )
        .distinct()
        .order_by(EvidencePassage.page_number)
    ).all()
    return [row for row in rows if row is not None]


@router.post("/{version_id}/reprocess", response_model=VersionInfo)
def reprocess_version(
    version_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AssetVersion:
    """Re-run FR-06 extraction for an existing version.

    Existing passages are replaced, but the stored original and its hash are
    never touched (NFR-05, BR-10).
    """
    version = _get_version(db, version_id)
    if version.processing_status == "PROCESSING":
        raise HTTPException(status_code=409, detail="version is already being processed")

    version.processing_status = "PENDING"
    version.processing_error = None
    db.commit()
    db.refresh(version)

    background.add_task(processing.process_version, version.id)
    return version
