from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from ..models import Article, ArticleClaim, Claim, ImpactAlert, ReviewEvent, User
from ..schemas.article import (
    ArticleClaimOut,
    ArticleCreate,
    ArticleGenerate,
    ArticleList,
    ArticleOut,
    ArticleSummary,
    PublicArticleOut,
    ReviewEventOut,
    TransitionRequest,
)
from ..schemas.claim import ClaimOut
from ..services import editorial
from ..services.authoring import llm_available
from ..services.editorial import record_event
from .claims import _to_out as claim_to_out
from .deps import CurrentUser, DbSession, require_role

router = APIRouter(tags=["articles"])

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def _slugify(title: str) -> str:
    slug = _SLUG_STRIP.sub("-", title.lower()).strip("-")[:120]
    return slug or "article"


def _unique_slug(db, title: str, exclude: int | None = None) -> str:
    base = _slugify(title)
    slug, suffix = base, 2
    while True:
        existing = db.scalar(select(Article.id).where(Article.slug == slug))
        if existing is None or existing == exclude:
            return slug
        slug = f"{base}-{suffix}"
        suffix += 1


def _open_alert_counts(db) -> dict[int, int]:
    rows = db.execute(
        select(ImpactAlert.article_id, func.count())
        .where(ImpactAlert.status == "OPEN", ImpactAlert.article_id.is_not(None))
        .group_by(ImpactAlert.article_id)
    ).all()
    return {article_id: int(total) for article_id, total in rows if article_id is not None}


def _to_summary(article: Article, open_alerts: dict[int, int]) -> ArticleSummary:
    out = ArticleSummary.model_validate(article)
    out.author_name = article.author.name if article.author else None
    out.claim_count = len(article.claims)
    out.open_alert_count = open_alerts.get(article.id, 0)
    return out


def _to_out(article: Article, db) -> ArticleOut:
    # Built field by field: claims need the evidence links resolved, which
    # from_attributes cannot do on the ArticleClaim join rows.
    summary = _to_summary(article, _open_alert_counts(db))
    return ArticleOut(
        id=summary.id,
        title=summary.title,
        slug=summary.slug,
        status=summary.status,
        summary=summary.summary,
        audience=summary.audience,
        author_id=summary.author_id,
        author_name=summary.author_name,
        generation_mode=summary.generation_mode,
        generation_model=article.generation_model,
        generation_note=article.generation_note,
        needs_reverification=article.needs_reverification,
        claim_count=summary.claim_count,
        open_alert_count=summary.open_alert_count,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
        published_at=summary.published_at,
        body=article.body,
        claims=[
            ArticleClaimOut(
                position=membership.position,
                claim=claim_to_out(membership.claim),
            )
            for membership in article.claims
        ],
        open_alerts=[
            int(alert_id)
            for alert_id in db.scalars(
                select(ImpactAlert.id).where(
                    ImpactAlert.article_id == article.id, ImpactAlert.status == "OPEN"
                )
            ).all()
        ],
    )


def _get_article(db, article_id: int) -> Article:
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="article not found")
    return article


def _ordered_claims(article: Article) -> list[Claim]:
    return [membership.claim for membership in article.claims]


@router.get("/articles", response_model=ArticleList)
def list_articles(
    db: DbSession,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
) -> ArticleList:
    stmt = select(Article)
    if status_filter:
        stmt = stmt.where(Article.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    open_alerts = _open_alert_counts(db)
    rows = db.scalars(stmt.order_by(Article.id.desc()).limit(limit)).all()
    return ArticleList(total=total, items=[_to_summary(row, open_alerts) for row in rows])


@router.get("/articles/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: DbSession) -> ArticleOut:
    return _to_out(_get_article(db, article_id), db)


@router.post("/articles", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(payload: ArticleCreate, db: DbSession, user: CurrentUser) -> ArticleOut:
    """FR-15 / FR-16 — assemble an article from claims and render its body."""
    require_role(user, "EDITOR")

    claims: list[Claim] = []
    for claim_id in payload.claim_ids:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise HTTPException(status_code=404, detail=f"claim {claim_id} not found")
        if not claim.evidence_links:
            raise HTTPException(status_code=422, detail=f"claim #{claim_id} has no evidence")
        claims.append(claim)

    article = Article(
        title=payload.title.strip(),
        slug=_unique_slug(db, payload.title),
        summary=payload.summary,
        audience=payload.audience,
        author_id=user.id,
        status="DRAFT",
    )
    db.add(article)
    db.flush()

    for position, claim in enumerate(claims):
        db.add(ArticleClaim(article_id=article.id, claim_id=claim.id, position=position))

    db.refresh(article)
    body, mode, model, note = editorial.render_body(article, claims)
    article.body = body
    article.generation_mode = mode
    article.generation_model = model
    article.generation_note = note

    editorial.record_event(db, action="ARTICLE_DRAFTED", actor=user, article_id=article.id, to_status="DRAFT")
    db.commit()
    db.refresh(article)
    return _to_out(article, db)


@router.post("/articles/{article_id}/generate", response_model=ArticleOut)
def regenerate(
    article_id: int,
    payload: ArticleGenerate,
    db: DbSession,
    user: CurrentUser,
) -> ArticleOut:
    """FR-17 — re-render the body; falls back to extractive when no LLM is configured."""
    require_role(user, "EDITOR")
    article = _get_article(db, article_id)
    claims = _ordered_claims(article)
    if not claims:
        raise HTTPException(status_code=422, detail="this article has no claims yet")

    try:
        body, mode, model, note = editorial.render_body(article, claims, payload.mode)
    except editorial.EditorialError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    article.body = body
    article.generation_mode = mode
    article.generation_model = model
    article.generation_note = note
    editorial.record_event(
        db, action="ARTICLE_REGENERATED", actor=user, article_id=article.id, comment=note
    )
    db.commit()
    db.refresh(article)
    return _to_out(article, db)


@router.post("/articles/{article_id}/transition", response_model=ArticleOut)
def move_article(
    article_id: int,
    payload: TransitionRequest,
    db: DbSession,
    user: CurrentUser,
    target: str = Query(...),
) -> ArticleOut:
    """FR-25 — draft → in_review → approved → published, with an audit row."""
    require_role(user, "EDITOR", "REVIEWER")
    article = _get_article(db, article_id)
    previous = article.status

    # Authorise before mutating: sign-off is the reviewer's job (FR-02), and
    # publishing may only follow approval (BR-07).
    if target in {"APPROVED", "REJECTED", "PUBLISHED"}:
        require_role(user, "REVIEWER")

    try:
        editorial.transition(article, target, user, payload.comment)
    except editorial.EditorialError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    editorial.record_event(
        db,
        action=f"ARTICLE_{target}",
        actor=user,
        article_id=article.id,
        comment=payload.comment,
        from_status=previous,
        to_status=target,
    )
    db.commit()
    db.refresh(article)
    return _to_out(article, db)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: int, db: DbSession, user: CurrentUser) -> None:
    """Remove an article and its claim memberships. Claims themselves survive —
    the claim library is the reusable asset, an article is one presentation."""
    require_role(user, "EDITOR")
    article = _get_article(db, article_id)
    db.delete(article)
    record_event(db, action="ARTICLE_DELETED", actor=user, article_id=article_id)
    db.commit()


@router.get("/articles/{article_id}/events", response_model=list[ReviewEventOut])
def article_events(article_id: int, db: DbSession) -> list[ReviewEventOut]:
    """BR-12 — who did what to this article, in order."""
    _get_article(db, article_id)
    rows = db.scalars(
        select(ReviewEvent).where(ReviewEvent.article_id == article_id).order_by(ReviewEvent.id)
    ).all()
    return [
        ReviewEventOut(
            id=row.id,
            action=row.action,
            comment=row.comment,
            from_status=row.from_status,
            to_status=row.to_status,
            actor_name=row.actor.name if row.actor else None,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/articles/by-slug/{slug}", response_model=PublicArticleOut)
def public_article(slug: str, db: DbSession) -> PublicArticleOut:
    """FR-27 — the reader-facing view. Only published articles are exposed."""
    article = db.scalar(select(Article).where(Article.slug == slug))
    if article is None or article.status != "PUBLISHED":
        raise HTTPException(status_code=404, detail="no published article at this address")

    return PublicArticleOut(
        title=article.title,
        summary=article.summary,
        body=article.body or "",
        author_name=article.author.name if article.author else None,
        published_at=article.published_at,
        audience=article.audience,
        claims=[claim_to_out(membership.claim) for membership in article.claims],
    )


@router.get("/capabilities", response_model=dict)
def capabilities() -> dict:
    """What the drafting step can do right now, so the UI can say so honestly."""
    return {"llm_available": llm_available(), "default_mode": "llm" if llm_available() else "extractive"}


__all__ = ["router"]