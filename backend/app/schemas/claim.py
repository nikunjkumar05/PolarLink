from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRef(BaseModel):
    """Compact citation payload: enough to render and deep-link a claim."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    passage_id: int
    asset_id: int
    asset_title: str
    version_id: int
    version_number: int
    page_number: int | None = None
    excerpt: str


class ClaimEvidenceLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    relation: str
    quote: str | None = None
    evidence: EvidenceRef | None = None
    # Set when the cited passage no longer exists in the current version.
    passage_missing: bool = False


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    topic: str | None = None
    status: str
    created_by_id: int | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    evidence_links: list[ClaimEvidenceLinkOut] = Field(default_factory=list)


class ClaimEvidenceIn(BaseModel):
    passage_id: int
    relation: str = Field(default="SUPPORTS")
    quote: str | None = Field(default=None, max_length=1000)


class ClaimCreate(BaseModel):
    text: str = Field(min_length=8, max_length=2000)
    topic: str | None = Field(default=None, max_length=200)
    evidence: list[ClaimEvidenceIn] = Field(min_length=1)


class ClaimUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=8, max_length=2000)
    topic: str | None = Field(default=None, max_length=200)


class ClaimList(BaseModel):
    total: int
    items: list[ClaimOut]