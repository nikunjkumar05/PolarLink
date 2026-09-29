from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..config import ALLOWED_ACCESS_LEVELS, ALLOWED_ASSET_TYPES


class AssetVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    version_number: int
    original_filename: str
    file_hash: str
    size_bytes: int
    mime_type: str | None = None
    page_count: int | None = None
    passage_count: int = 0
    processing_status: str
    processing_error: str | None = None
    processing_note: str | None = None
    note: str | None = None
    uploaded_at: datetime


class AssetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    asset_type: str
    topic: str | None = None
    expedition: str | None = None
    station: str | None = None
    year: int | None = None
    author: str | None = None
    keywords: str | None = None
    attribution: str | None = None
    source: str | None = None
    access_level: str
    created_at: datetime
    updated_at: datetime
    version_count: int = 0
    latest_version: AssetVersionOut | None = None


class AssetDetail(AssetSummary):
    versions: list[AssetVersionOut] = []


class AssetList(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AssetSummary]


class AssetCreate(BaseModel):
    """FR-04 metadata supplied alongside an upload."""

    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    asset_type: str = Field(default="OTHER")
    topic: str | None = None
    expedition: str | None = None
    station: str | None = None
    year: int | None = Field(default=None, ge=1800, le=2200)
    author: str | None = None
    keywords: str | None = None
    attribution: str | None = None
    source: str | None = None
    access_level: str = "PUBLIC"
    note: str | None = None

    def normalized(self) -> AssetCreate:
        data = self.model_dump()
        if data["asset_type"] not in ALLOWED_ASSET_TYPES:
            data["asset_type"] = "OTHER"
        if data["access_level"] not in ALLOWED_ACCESS_LEVELS:
            data["access_level"] = "PUBLIC"
        for key in ("title", "topic", "expedition", "station", "author", "attribution", "source"):
            if isinstance(data.get(key), str):
                data[key] = data[key].strip() or None
        for key in ("description", "keywords", "note"):
            if isinstance(data.get(key), str):
                data[key] = data[key].strip() or None
        return AssetCreate(**data)


class AssetUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    asset_type: str | None = None
    topic: str | None = None
    expedition: str | None = None
    station: str | None = None
    year: int | None = Field(default=None, ge=1800, le=2200)
    author: str | None = None
    keywords: str | None = None
    attribution: str | None = None
    source: str | None = None
    access_level: str | None = None


class FilterOptions(BaseModel):
    asset_types: list[str]
    access_levels: list[str]
    expeditions: list[str]
    stations: list[str]
    topics: list[str]
    years: list[int]


class Message(BaseModel):
    detail: str
