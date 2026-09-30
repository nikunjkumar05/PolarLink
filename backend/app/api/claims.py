from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from ..models import LINK_RELATIONS, Claim, ClaimEvidenceLink, EvidencePassage, ReviewEvent
from ..schemas.claim import (
    ClaimCreate,
    ClaimEvidenceIn,
    ClaimEvidenceLinkOut,
    ClaimList,
    ClaimOut,
    ClaimUpdate,
)
from ..services import editorial
from ..services.extract import summarise
from .deps import CurrentUser, DbSession, require_role

router = APIRouter(prefix="/claims", tags=["claims"])


def _evidence_ref(link: ClaimEvidenceLink) -> tuple[dict | None, bool]:
    passage = link.passage
    if passage is None:
        return None, True
    version = passage.asset_version
    asset = version.asset if version else None
    return {
        "id": link.id,
        "passage_id": passage.id,
        "asset_id": passage.asset_id,
        "asset_title": asset.title if asset else "Unknown source",
        "version_id": passage.asset_version_id,
        "version_number": version.version_number if version else 0,
        "page_number": passage.page_number,
        "excerpt": summarise(passage.content, 260),
    }, False


def _to_out(claim: Claim) -> ClaimOut:
    out = ClaimOut.model_validate(claim)
    links: list[ClaimEvidenceLinkOut] = []
    for link in claim.evidence_links:
        ref, missing = _evidence_ref(link)
        links.append(
            ClaimEvidenceLinkOut(
                id=link.id,
                relation=link.relation,
                quote=link.quote,
                evidence=ref,
                passage_missing=missing,
            )
        )
    out.evidence_links = links
    return out


def _get_claim(db, claim_id: int) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="claim not found")
    return claim


@router.get("", response_model=ClaimList)
def list_claims(
    db: DbSession,
    status_filter: str | None = Query(None, alias="status"),
    topic: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> ClaimList:
    """FR-19 — browse the claim library."""
    stmt = select(Claim)
    if status_filter:
        stmt = stmt.where(Claim.status == status_filter)
    if topic:
        stmt = stmt.where(Claim.topic == topic)
    if q and q.strip():
        stmt = stmt.where(Claim.text.ilike(f"%{q.strip()}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Claim.id.desc()).limit(limit)).all()
    return ClaimList(total=total, items=[_to_out(row) for row in rows])


@router.get("/topics", response_model=list[str])
def claim_topics(db: DbSession) -> list[str]:
    rows = db.scalars(
        select(Claim.topic).where(Claim.topic.is_not(None)).distinct().order_by(Claim.topic)
    ).all()
    return [row for row in rows if row]


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: int, db: DbSession) -> Claim:
    return _to_out(_get_claim(db, claim_id))


@router.post("", response_model=ClaimOut, status_code=status.HTTP_201_CREATED)
def create_claim(payload: ClaimCreate, db: DbSession, user: CurrentUser) -> Claim:
    """FR-19 / FR-20 — a claim cannot exist without at least one evidence passage."""
    require_role(user, "EDITOR", "REVIEWER")

    for item in payload.evidence:
        if item.relation not in LINK_RELATIONS:
            raise HTTPException(status_code=422, detail=f"relation must be one of {LINK_RELATIONS}")
        if db.get(EvidencePassage, item.passage_id) is None:
            raise HTTPException(status_code=404, detail=f"passage {item.passage_id} not found")

    claim = Claim(text=payload.text.strip(), topic=payload.topic, created_by_id=user.id, status="SUPPORTED")
    db.add(claim)
    db.flush()

    for item in payload.evidence:
        passage = db.get(EvidencePassage, item.passage_id)
        db.add(
            ClaimEvidenceLink(
                claim_id=claim.id,
                passage_id=item.passage_id,
                relation=item.relation,
                quote=item.quote or (passage.content[:400] if passage else None),
            )
        )

    editorial.record_event(db, action="CLAIM_CREATED", actor=user, claim_id=claim.id)
    db.commit()
    db.refresh(claim)
    return _to_out(claim)


@router.patch("/{claim_id}", response_model=ClaimOut)
def update_claim(claim_id: int, payload: ClaimUpdate, db: DbSession, user: CurrentUser) -> Claim:
    require_role(user, "EDITOR", "REVIEWER")
    claim = _get_claim(db, claim_id)
    if payload.text is not None:
        claim.text = payload.text.strip()
    if payload.topic is not None:
        claim.topic = payload.topic
    db.commit()
    db.refresh(claim)
    return _to_out(claim)


@router.post("/{claim_id}/status", response_model=ClaimOut)
def set_claim_status(
    claim_id: int,
    db: DbSession,
    user: CurrentUser,
    new_status: str = Query(..., alias="status"),
    comment: str | None = Query(None),
) -> Claim:
    """FR-21 — a reviewer accepts or disputes a claim."""
    require_role(user, "REVIEWER")
    if new_status not in {"SUPPORTED", "DISPUTED", "REJECTED", "DRAFT"}:
        raise HTTPException(status_code=422, detail="unsupported claim status")

    claim = _get_claim(db, claim_id)
    previous = claim.status
    claim.status = new_status
    editorial.record_event(
        db,
        action="CLAIM_STATUS",
        actor=user,
        claim_id=claim.id,
        comment=comment,
        from_status=previous,
        to_status=new_status,
    )
    db.commit()
    db.refresh(claim)
    return _to_out(claim)


@router.delete("/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(claim_id: int, db: DbSession, user: CurrentUser) -> None:
    """Drop a claim and its evidence links. Published articles that used it keep
    their rendered body but lose the claim, so block that case explicitly."""
    require_role(user, "EDITOR")
    claim = _get_claim(db, claim_id)

    from ..models import ArticleClaim

    used = db.scalar(
        select(func.count())
        .select_from(ArticleClaim)
        .where(ArticleClaim.claim_id == claim_id)
    )
    if used:
        raise HTTPException(
            status_code=409,
            detail="remove this claim from its articles before deleting it",
        )

    db.delete(claim)
    db.commit()


@router.get("/{claim_id}/events", response_model=list[dict])
def claim_events(claim_id: int, db: DbSession) -> list[dict]:
    """BR-12 — the audit trail shown on the claim."""
    _get_claim(db, claim_id)
    rows = db.scalars(
        select(ReviewEvent).where(ReviewEvent.claim_id == claim_id).order_by(ReviewEvent.id)
    ).all()
    return [
        {
            "id": row.id,
            "action": row.action,
            "comment": row.comment,
            "from_status": row.from_status,
            "to_status": row.to_status,
            "actor_name": row.actor.name if row.actor else None,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


__all__ = ["router"]