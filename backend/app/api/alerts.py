from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from ..models import Asset, AssetVersion, EvidencePassage, ImpactAlert, ReviewEvent
from ..schemas.alert import AlertList, AlertOut, ResolveRequest, VersionChangeOut
from ..services import editorial
from .deps import CurrentUser, DbSession, require_role

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _to_out(alert: ImpactAlert) -> AlertOut:
    out = AlertOut.model_validate(alert)
    out.article_title = alert.article.title if alert.article else None
    out.claim_text = alert.claim.text if alert.claim else ""
    out.asset_title = alert.asset.title if alert.asset else "Unknown source"
    out.previous_version_number = (
        alert.previous_version.version_number if alert.previous_version else 0
    )
    out.current_version_number = (
        alert.current_version.version_number if alert.current_version else 0
    )
    out.resolved_by_name = alert.resolved_by.name if alert.resolved_by else None
    if alert.current_passage_id:
        passage = alert.current_passage or None
        out.current_page_number = passage.page_number if passage else None
    return out


@router.get("", response_model=AlertList)
def list_alerts(
    db: DbSession,
    status_filter: str | None = Query(None, alias="status"),
    article_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> AlertList:
    """FR-38 — the re-verification inbox."""
    stmt = select(ImpactAlert)
    if status_filter:
        stmt = stmt.where(ImpactAlert.status == status_filter)
    if article_id:
        stmt = stmt.where(ImpactAlert.article_id == article_id)

    open_total = db.scalar(
        select(func.count()).select_from(
            select(ImpactAlert).where(ImpactAlert.status == "OPEN").subquery()
        )
    ) or 0
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(ImpactAlert.created_at.desc(), ImpactAlert.id.desc()).limit(limit)).all()
    return AlertList(
        total=int(total),
        open_total=int(open_total),
        items=[_to_out(row) for row in rows],
    )


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: int, db: DbSession) -> AlertOut:
    alert = db.get(ImpactAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return _to_out(alert)


@router.post("/{alert_id}/resolve", response_model=AlertOut)
def resolve(
    alert_id: int,
    payload: ResolveRequest,
    db: DbSession,
    user: CurrentUser,
) -> AlertOut:
    """FR-42 — a reviewer confirms the claim still matches the changed source."""
    require_role(user, "REVIEWER")
    alert = db.get(ImpactAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    if alert.status != "OPEN":
        raise HTTPException(status_code=409, detail="this alert is already closed")

    try:
        editorial.resolve_alert(
            db,
            alert,
            status=payload.status,
            note=payload.note,
            actor=user,
            current_passage_id=payload.current_passage_id,
        )
    except editorial.EditorialError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    db.refresh(alert)
    return _to_out(alert)


@router.get("/asset/{asset_id}/changes", response_model=VersionChangeOut)
def asset_changes(asset_id: int, db: DbSession) -> VersionChangeOut:
    """FR-31 — compare the two newest versions of an asset."""
    from ..services.diffing import diff_passages

    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")

    versions = sorted(asset.versions, key=lambda v: v.version_number)
    if len(versions) < 2:
        raise HTTPException(status_code=404, detail="this asset has only one version")

    previous, current = versions[-2], versions[-1]
    previous_passages = list(db.scalars(select(EvidencePassage).where(
        EvidencePassage.asset_version_id == previous.id
    ).order_by(EvidencePassage.sequence_number)).all())
    current_passages = list(db.scalars(select(EvidencePassage).where(
        EvidencePassage.asset_version_id == current.id
    ).order_by(EvidencePassage.sequence_number)).all())

    diff = diff_passages(previous_passages, current_passages)
    affected = editorial.apply_change(
        db, asset=asset, previous_version=previous, current_version=current, diff=diff
    )
    db.commit()

    return VersionChangeOut(
        asset_id=asset.id,
        asset_title=asset.title,
        previous_version_id=previous.id,
        previous_version_number=previous.version_number,
        previous_hash=previous.file_hash,
        current_version_id=current.id,
        current_version_number=current.version_number,
        current_hash=current.file_hash,
        changed=previous.file_hash != current.file_hash,
        added=diff.added,
        removed=diff.removed,
        modified=diff.modified,
        affected_claims=len({alert.claim_id for alert in affected}),
        affected_articles=len({alert.article_id for alert in affected if alert.article_id}),
    )


@router.get("/{alert_id}/passages", response_model=list[dict])
def alert_passages(alert_id: int, db: DbSession) -> list[dict]:
    """Candidate replacements so a reviewer can re-anchor the claim in one click."""
    alert = db.get(ImpactAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")

    rows = db.scalars(
        select(EvidencePassage)
        .where(EvidencePassage.asset_version_id == alert.current_version_id)
        .order_by(EvidencePassage.sequence_number)
    ).all()
    return [
        {
            "id": passage.id,
            "page_number": passage.page_number,
            "sequence_number": passage.sequence_number,
            "excerpt": passage.content[:240],
        }
        for passage in rows
    ]


__all__ = ["router"]