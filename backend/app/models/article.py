from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

# FR-25 review workflow. PUBLISHED is reachable only from APPROVED (BR-07).
ARTICLE_STATUSES = ("DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED", "REJECTED")
# Legal transitions — enforced in services/editorial.py, not in the UI alone.
ARTICLE_TRANSITIONS = {
    "DRAFT": ("IN_REVIEW",),
    "IN_REVIEW": ("APPROVED", "REJECTED", "DRAFT"),
    "REJECTED": ("DRAFT",),
    "APPROVED": ("PUBLISHED", "DRAFT"),
    "PUBLISHED": ("APPROVED",),
}
# FR-38 — what a source change does to a live publication.
ALERT_STATUSES = ("OPEN", "REVERIFIED", "ACKNOWLEDGED")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Article(Base):
    """FR-15 — outreach content assembled from claims, never from raw prose."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Rendered from the claims at build time (FR-17), citation markers included.
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "extractive" when composed from source quotes, "llm" when an LLM drafted it.
    generation_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    generation_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    generation_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)
    audience: Mapped[str | None] = mapped_column(String(120), nullable=True)

    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # FR-31 / FR-40 — a published article can be flagged for re-verification.
    needs_reverification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    author = relationship("User", lazy="joined")
    claims = relationship(
        "ArticleClaim",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="ArticleClaim.position",
        lazy="selectin",
    )

    __table_args__ = (Index("ix_articles_status_published", "status", "published_at"),)


class ArticleClaim(Base):
    """Ordered claim membership of an article (FR-16)."""

    __tablename__ = "article_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    article = relationship("Article", back_populates="claims")
    claim = relationship("Claim", lazy="joined")

    __table_args__ = (UniqueConstraint("article_id", "claim_id", name="uq_article_claim"),)


class ImpactAlert(Base):
    """FR-37 — a changed source broke the evidence behind a live claim.

    Created when a new asset version alters a passage that a claim cited. The
    quote from the previous version is snapshotted so the reviewer can compare
    without opening the old file.
    """

    __tablename__ = "impact_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_version_id: Mapped[int] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="CASCADE"), nullable=False
    )
    current_version_id: Mapped[int] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="CASCADE"), nullable=False
    )

    previous_passage_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_passage_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_passages.id", ondelete="SET NULL"), nullable=True
    )
    previous_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="MODIFIED")

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    claim = relationship("Claim", lazy="joined")
    article = relationship("Article", lazy="joined")
    asset = relationship("Asset", lazy="joined")
    resolved_by = relationship("User", lazy="joined")
    previous_version = relationship("AssetVersion", foreign_keys=[previous_version_id])
    current_version = relationship("AssetVersion", foreign_keys=[current_version_id])
    # The old passage is referenced by id only: it may be deleted on reprocess,
    # and the snapshot in previous_quote is what the reviewer compares against.
    current_passage = relationship("EvidencePassage", foreign_keys=[current_passage_id])

    __table_args__ = (Index("ix_impact_alerts_status_created", "status", "created_at"),)


__all__ = [
    "ALERT_STATUSES",
    "ARTICLE_STATUSES",
    "ARTICLE_TRANSITIONS",
    "Article",
    "ArticleClaim",
    "ImpactAlert",
    "utcnow",
]