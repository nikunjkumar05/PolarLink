from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidencePassageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_version_id: int
    asset_id: int
    sequence_number: int
    location_type: str
    content: str
    page_number: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    char_count: int
    created_at: datetime


class VersionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    version_number: int
    original_filename: str
    processing_status: str
    processing_error: str | None = None
    processing_note: str | None = None
    page_count: int | None = None
    passage_count: int


class PassageList(BaseModel):
    total: int
    page: int
    page_size: int
    version: VersionInfo
    items: list[EvidencePassageOut]
