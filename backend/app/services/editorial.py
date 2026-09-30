from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    ARTICLE_TRANSITIONS,
    Article,
    ArticleClaim,
    Claim,
    ClaimEvidenceLink,
    EvidencePassage,
    ImpactAlert,
    ReviewEvent,
    User,
)
from ..models.article import utcnow
from .authoring import compose_extractive, draft_with_llm, llm_available, llm_note
from .diffing import DiffResult

log = logging.getLogger(__name__)


class EditorialError(ValueError):
    """A rule of the workflow was broken; the API turns this into a 4xx."""


# ---------------------------------------------------------------- generation


def claim_payload(claim: Claim) -> dict:
    quotes = [
        link.quote or (link.passage.content if link.passage else "")
        for link in claim.evidence_links
    ]
    return {"id": claim.id, "text": claim.text, "quotes": [q for q in quotes if q]}


def render_body(
    article: Article, claims: list[Claim], mode: str = "auto"
) -> tuple[str, str, str | None, str | None]:
    """FR-17 — build the article body from its claims.

    Returns (body, generation_mode, generation_model, note). The LLM path is
    optional; if it is unavailable or returns something unusable we fall back
    to the extractive composer rather than shipping an empty draft.
    """
    payloads = [claim_payload(claim) for claim in claims]
    note = llm_note()

    if mode in {"auto", "llm"} and llm_available() and payloads:
        try:
            body, model, llm_note_text = draft_with_llm(payloads)
            return body, "llm", model, llm_note_text
        except RuntimeError as exc:
            if mode == "llm":
                raise EditorialError(str(exc)) from exc
            note = f"LLM drafting unavailable ({exc}); composed extractively instead."

    return compose_extractive(article.title, payloads, article.summary), "extractive", None, note


# ---------------------------------------------------------------- transitions


def transition(article: Article, target: str, actor: User, comment: str | None) -> None:
    """FR-25 — move an article through the review workflow, with an audit row."""
    allowed = ARTICLE_TRANSITIONS.get(article.status, ())
    if target not in allowed:
        raise EditorialError(
            f"cannot move an article from {article.status} to {target}"
        )

    if target == "IN_REVIEW":
        _require_citable(article)

    if target == "PUBLISHED":
        article.published_at = utcnow()

    if target == "DRAFT":
        article.needs_reverification = False

    article.status = target


def record_event(
    db: Session,
    *,
    action: str,
    actor: User | None,
    article_id: int | None = None,
    claim_id: int | None = None,
    alert_id: int | None = None,
    comment: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
) -> ReviewEvent:
    event = ReviewEvent(
        article_id=article_id,
        claim_id=claim_id,
        alert_id=alert_id,
        actor_id=actor.id if actor else None,
        action=action,
        comment=comment,
        from_status=from_status,
        to_status=to_status,
    )
    db.add(event)
    return event


def _require_citable(article: Article) -> None:
    """FR-20 / BR-06 — nothing ungrounded may enter review or publication."""
    if not article.claims:
        raise EditorialError("an article needs at least one claim before review")
    for membership in article.claims:
        claim = membership.claim
        if not claim.evidence_links:
            raise EditorialError(f"claim #{claim.id} has no evidence")
        if claim.status in {"DRAFT", "DISPUTED", "REJECTED"}:
            raise EditorialError(
                f"claim #{claim.id} is {claim.status.lower()} — mark it supported first"
            )


# ---------------------------------------------------------------- change impact


def apply_change(
    db: Session,
    *,
    asset,
    previous_version,
    current_version,
    diff: DiffResult,
) -> list[ImpactAlert]:
    """FR-37 / FR-40 — flag published articles whose evidence just changed.

    A claim is affected when the passage it cited was modified or removed in
    the new version. Claims are marked STALE, their articles flagged
    ``needs_reverification`` and one alert per (article, claim) is raised.
    """
    affected_previous_ids = {
        change.previous_id for change in diff.touched if change.previous_id is not None
    }
    if not affected_previous_ids:
        return []

    links = list(
        db.scalars(
            select(ClaimEvidenceLink).where(
                ClaimEvidenceLink.passage_id.in_(affected_previous_ids)
            )
        ).all()
    )
    if not links:
        return []

    claims = {
        claim.id: claim
        for claim in db.scalars(
            select(Claim).where(Claim.id.in_({link.claim_id for link in links}))
        ).all()
    }

    change_by_previous = {
        change.previous_id: change for change in diff.touched if change.previous_id
    }

    membership_rows = list(
        db.execute(
            select(ArticleClaim, Article)
            .join(Article, Article.id == ArticleClaim.article_id)
            .where(ArticleClaim.claim_id.in_(claims.keys()))
        ).all()
    )
    article_by_claim: dict[int, list[Article]] = {}
    for membership, article in membership_rows:
        article_by_claim.setdefault(membership.claim_id, []).append(article)

    alerts: list[ImpactAlert] = []
    for link in links:
        claim = claims.get(link.claim_id)
        if claim is None:
            continue
        change = change_by_previous.get(link.passage_id)
        if change is None:
            continue

        claim.status = "STALE"
        reason = _reason_text(change, asset.title)

        for article in article_by_claim.get(claim.id, []):
            if article.status == "PUBLISHED":
                article.needs_reverification = True
            alert = ImpactAlert(
                article_id=article.id,
                claim_id=claim.id,
                asset_id=asset.id,
                previous_version_id=previous_version.id,
                current_version_id=current_version.id,
                previous_passage_id=link.passage_id,
                current_passage_id=change.current_id,
                previous_quote=(link.quote or (change.previous.content if change.previous else None)),
                current_quote=(change.current.content if change.current else None),
                change_kind=change.kind,
                reason=reason,
                status="OPEN",
            )
            db.add(alert)
            record_event(
                db,
                action="SOURCE_CHANGED",
                actor=None,
                article_id=article.id,
                claim_id=claim.id,
                comment=reason,
            )
            alerts.append(alert)

    db.flush()
    return alerts


def _reason_text(change, asset_title: str) -> str:
    if change.kind == "REMOVED":
        return (
            f"The passage cited by this claim no longer appears in {asset_title}; "
            "the wording may have been deleted or moved."
        )
    return (
        f"The passage cited by this claim was edited in {asset_title}. "
        "Confirm the claim still matches the source, then re-verify it."
    )


def resolve_alert(
    db: Session,
    alert: ImpactAlert,
    *,
    status: str,
    note: str | None,
    actor: User,
    current_passage_id: int | None = None,
) -> ImpactAlert:
    """FR-42 — close an alert and, optionally, re-anchor the claim."""
    alert.status = status
    alert.resolution_note = note
    alert.resolved_by_id = actor.id
    alert.resolved_at = utcnow()

    claim = alert.claim
    if status == "REVERIFIED":
        if current_passage_id is not None:
            passage = db.get(EvidencePassage, current_passage_id)
            if passage is None or passage.asset_id != alert.asset_id:
                raise EditorialError("that passage is not part of this asset")
            link = next(
                (l for l in claim.evidence_links if l.id == alert.previous_passage_id),
                None,
            )
            if link is None:
                link = ClaimEvidenceLink(
                    claim_id=claim.id,
                    passage_id=current_passage_id,
                    relation="SUPPORTS",
                    quote=passage.content[:400],
                )
                db.add(link)
            else:
                link.passage_id = current_passage_id
                link.quote = passage.content[:400]
        claim.status = "VERIFIED"
        claim.verified_at = alert.resolved_at
        claim.verified_by_id = actor.id

        if alert.article is not None:
            still_open = [
                other
                for other in db.scalars(
                    select(ImpactAlert).where(
                        ImpactAlert.article_id == alert.article_id,
                        ImpactAlert.status == "OPEN",
                        ImpactAlert.id != alert.id,
                    )
                ).all()
            ]
            if not still_open:
                alert.article.needs_reverification = False

    record_event(
        db,
        action=status,
        actor=actor,
        article_id=alert.article_id,
        claim_id=alert.claim_id,
        alert_id=alert.id,
        comment=note,
        from_status="OPEN",
        to_status=status,
    )
    return alert


__all__ = [
    "EditorialError",
    "apply_change",
    "claim_payload",
    "record_event",
    "render_body",
    "resolve_alert",
    "transition",
]