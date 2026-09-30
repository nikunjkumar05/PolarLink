from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article_id: int | None = None
    article_title: str | None = None
    claim_id: int
    claim_text: str = ""
    asset_id: int
    asset_title: str = ""
    previous_version_id: int
    previous_version_number: int = 0
    current_version_id: int
    current_version_number: int = 0
    previous_quote: str | None = None
    current_quote: str | None = None
    current_page_number: int | None = None
    previous_passage_id: int | None = None
    current_passage_id: int | None = None
    change_kind: str = "MODIFIED"
    reason: str
    status: str
    resolution_note: str | None = None
    resolved_at: datetime | None = None
    resolved_by_name: str | None = None
    created_at: datetime


class AlertList(BaseModel):
    total: int
    open_total: int
    items: list[AlertOut]


class ResolveRequest(BaseModel):
    status: str = Field(pattern="^(REVERIFIED|ACKNOWLEDGED)$")
    note: str | None = Field(default=None, max_length=1000)
    # When REVERIFIED, relink the claim to the passage in the current version.
    current_passage_id: int | None = None


class VersionChangeOut(BaseModel):
    """FR-31 — what changed between two immutable versions of one asset."""

    asset_id: int
    asset_title: str
    previous_version_id: int
    previous_version_number: int
    previous_hash: str
    current_version_id: int
    current_version_number: int
    current_hash: str
    changed: bool
    added: int = 0
    removed: int = 0
    modified: int = 0
    affected_claims: int = 0
    affected_articles: int = 0