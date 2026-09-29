from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from ..config import ALLOWED_ACCESS_LEVELS, ALLOWED_ASSET_TYPES, ALLOWED_PROCESSING_STATUSES
from ..db import Base

if TYPE_CHECKING:
    from .evidence import EvidencePassage


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    """FR-03 / FR-04 / FR-05 — the logical resource and its metadata."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FR-04 metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False, default="OTHER")
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    expedition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    station: Mapped[str | None] = mapped_column(String(200), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    author: Mapped[str | None] = mapped_column(String(300), nullable=True)
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribution: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # FR-01 / access control surface
    access_level: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLIC")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    versions: Mapped[list[AssetVersion]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="AssetVersion.version_number",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_assets_asset_type", "asset_type"),
        Index("ix_assets_expedition", "expedition"),
        Index("ix_assets_station", "station"),
        Index("ix_assets_year", "year"),
        Index("ix_assets_topic", "topic"),
        Index("ix_assets_access_level", "access_level"),
    )

    @property
    def version_count(self) -> int:
        return len(self.versions)

    @property
    def latest_version(self) -> AssetVersion | None:
        return self.versions[-1] if self.versions else None


class AssetVersion(Base):
    """FR-29 / BR-01 / BR-02 — immutable version of an asset."""

    __tablename__ = "asset_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # upload-processing status (FR-06)
    processing_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING"
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    asset: Mapped[Asset] = relationship(back_populates="versions")
    passages: Mapped[list["EvidencePassage"]] = relationship(
        back_populates="asset_version",
        cascade="all, delete-orphan",
        order_by="EvidencePassage.sequence_number",
        lazy="noload",
    )

    __table_args__ = (
        UniqueConstraint("asset_id", "version_number", name="uq_asset_version_number"),
        Index("ix_asset_versions_status", "processing_status"),
    )


__all__ = ["Asset", "AssetVersion"]

_ALLOWED = {
    "asset_type": ALLOWED_ASSET_TYPES,
    "access_level": ALLOWED_ACCESS_LEVELS,
    "processing_status": ALLOWED_PROCESSING_STATUSES,
}
