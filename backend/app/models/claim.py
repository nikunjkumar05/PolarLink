from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
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

# FR-19 claim lifecycle. A claim is only publishable while SUPPORTED.
CLAIM_STATUSES = ("DRAFT", "SUPPORTED", "DISPUTED", "REJECTED", "STALE", "VERIFIED")
# FR-20 — how a passage relates to a claim.
LINK_RELATIONS = ("SUPPORTS", "CONTRADICTS")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Claim(Base):
    """FR-19 — one atomic, citable assertion drawn from the archive."""

    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Set when a reviewer confirms the claim still matches its evidence after the
    # source changed (FR-42). Cleared again if the source moves once more.
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    evidence_links = relationship(
        "ClaimEvidenceLink",
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="ClaimEvidenceLink.id",
        lazy="selectin",
    )

    __table_args__ = (Index("ix_claims_status_topic", "status", "topic"),)


class ClaimEvidenceLink(Base):
    """FR-20 — the mandatory evidence anchor: every claim cites a passage."""

    __tablename__ = "claim_evidence_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    passage_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_passages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation: Mapped[str] = mapped_column(String(32), nullable=False, default="SUPPORTS")
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    claim = relationship("Claim", back_populates="evidence_links")
    passage = relationship("EvidencePassage", lazy="joined")

    __table_args__ = (
        UniqueConstraint("claim_id", "passage_id", name="uq_claim_evidence"),
    )


__all__ = ["CLAIM_STATUSES", "Claim", "ClaimEvidenceLink", "LINK_RELATIONS", "utcnow"]