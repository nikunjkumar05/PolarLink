from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

# FR-02 roles. EDITOR authors drafts, REVIEWER signs off, ADMIN does both.
ROLES = ("ADMIN", "EDITOR", "REVIEWER")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """FR-01 — the person behind every editorial action."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="EDITOR")
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    review_events = relationship(
        "ReviewEvent", back_populates="actor", cascade="all, delete-orphan"
    )


class ReviewEvent(Base):
    """FR-21 / BR-12 — append-only audit trail of editorial decisions."""

    __tablename__ = "review_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    claim_id: Mapped[int | None] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), nullable=True, index=True
    )
    alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("impact_alerts.id", ondelete="CASCADE"), nullable=True, index=True
    )

    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    actor = relationship("User", back_populates="review_events")


__all__ = ["ROLES", "ReviewEvent", "User", "utcnow"]