from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BLOB,
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

# FR-13 — evidence lives at a location inside one specific AssetVersion (BR-03).
LOCATION_TYPES = ("PAGE", "TIMESTAMP", "TABLE", "TEXT")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EvidencePassage(Base):
    __tablename__ = "evidence_passages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    asset_version_id: Mapped[int] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    location_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PAGE")
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # PDF location (FR-13)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Offsets inside the extracted text of that page, for highlighting (FR-14)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Video transcript location (FR-08), unused until the video module lands
    start_timestamp: Mapped[float | None] = mapped_column(nullable=True)
    end_timestamp: Mapped[float | None] = mapped_column(nullable=True)

    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # FR-11 semantic search — float32 vector bytes plus the model that produced
    # them, so a model change can be detected and the passages re-embedded.
    embedding: Mapped[bytes | None] = mapped_column(BLOB, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    asset_version = relationship("AssetVersion", back_populates="passages")

    __table_args__ = (
        UniqueConstraint("asset_version_id", "sequence_number", name="uq_passage_sequence"),
        Index("ix_evidence_passages_page", "asset_version_id", "page_number"),
    )


__all__ = ["EvidencePassage", "LOCATION_TYPES"]
