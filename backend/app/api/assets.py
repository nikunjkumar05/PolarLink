from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from ..config import ALLOWED_ACCESS_LEVELS, ALLOWED_ASSET_TYPES, MAX_UPLOAD_BYTES
from ..db import get_db
from ..models import Asset, AssetVersion
from ..schemas import (
    AssetCreate,
    AssetDetail,
    AssetList,
    AssetSummary,
    AssetUpdate,
    AssetVersionOut,
    FilterOptions,
)
from ..services import processing, storage

router = APIRouter(prefix="/assets", tags=["assets"])

_HEAD_BYTES = 8192


def _parse_meta(meta: str | None, fallback_title: str) -> AssetCreate:
    if meta:
        try:
            payload = json.loads(meta)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"metadata is not valid JSON: {exc}")
    else:
        payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="metadata must be a JSON object")
    payload.setdefault("title", fallback_title)
    try:
        return AssetCreate(**payload).normalized()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


async def _peek(upload: UploadFile) -> bytes:
    """Read the magic bytes used for content sniffing, then rewind the stream."""
    head = await upload.read(_HEAD_BYTES)
    await upload.seek(0)
    return head


def _next_version_number(db: Session, asset_id: int) -> int:
    current = db.scalar(
        select(func.max(AssetVersion.version_number)).where(AssetVersion.asset_id == asset_id)
    )
    return (current or 0) + 1


def _add_version(
    db: Session,
    asset: Asset,
    filename: str,
    stream,
    head: bytes,
    declared_type: str | None,
    note: str | None,
) -> AssetVersion:
    version_number = _next_version_number(db, asset.id)
    try:
        stored = storage.store_file(
            asset.id, version_number, filename, stream, max_bytes=MAX_UPLOAD_BYTES
        )
    except storage.EmptyUpload:
        raise HTTPException(status_code=422, detail="uploaded file is empty")
    except storage.UploadTooLarge:
        raise HTTPException(status_code=413, detail="file exceeds upload limit")

    mime = storage.sniff_mime(head, filename) or declared_type
    version = AssetVersion(
        asset_id=asset.id,
        version_number=version_number,
        original_filename=filename,
        file_path=stored.relative_path,
        file_hash=stored.file_hash,
        size_bytes=stored.size_bytes,
        mime_type=declared_type if declared_type and declared_type != "application/octet-stream" else mime,
        processing_status="PENDING",
        note=note,
    )
    db.add(version)
    db.flush()
    return version


@router.post("", response_model=AssetDetail, status_code=201)
async def create_asset(
    background: BackgroundTasks,
    file: UploadFile = File(..., description="original source file"),
    meta: str = Form("{}"),
    db: Session = Depends(get_db),
) -> Asset:
    """FR-03 asset upload + FR-04 metadata + FR-29 first AssetVersion."""
    filename = storage.safe_filename(file.filename or "file")
    payload = _parse_meta(meta, fallback_title=filename)
    head = await _peek(file)

    asset = Asset(**payload.model_dump(exclude={"note"}))
    db.add(asset)
    db.flush()

    try:
        version = _add_version(
            db, asset, filename, file.file, head, file.content_type, payload.note
        )
        db.commit()
    except HTTPException:
        db.rollback()
        storage.delete_asset_dir(asset.id)
        raise

    # FR-06 extraction runs after the response so uploads stay responsive (NFR-02).
    background.add_task(processing.process_version, version.id)
    db.refresh(asset)
    return asset


@router.post("/{asset_id}/versions", response_model=AssetVersionOut, status_code=201)
async def create_version(
    asset_id: int,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
) -> AssetVersion:
    """FR-29 — upload a new immutable version of an existing asset."""
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")

    filename = storage.safe_filename(file.filename or "file")
    head = await _peek(file)
    version = _add_version(db, asset, filename, file.file, head, file.content_type, note)
    db.commit()

    background.add_task(processing.process_version, version.id)
    db.refresh(version)
    return version


@router.get("", response_model=AssetList)
def list_assets(
    q: str | None = Query(None, description="title / description / keyword match"),
    asset_type: list[str] | None = Query(None),
    expedition: list[str] | None = Query(None),
    station: list[str] | None = Query(None),
    topic: list[str] | None = Query(None),
    year: list[int] | None = Query(None),
    access_level: list[str] | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AssetList:
    """FR-10 keyword search + FR-12 search filtering over the repository."""
    stmt: Select = select(Asset)
    stmt = _apply_filters(stmt, q, asset_type, expedition, station, topic, year, access_level)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Asset.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return AssetList(
        total=total,
        page=page,
        page_size=page_size,
        items=[AssetSummary.model_validate(r) for r in rows],
    )


def _apply_filters(
    stmt: Select,
    q: str | None,
    asset_type: list[str] | None,
    expedition: list[str] | None,
    station: list[str] | None,
    topic: list[str] | None,
    year: list[int] | None,
    access_level: list[str] | None,
) -> Select:
    if q and q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Asset.title.ilike(needle),
                Asset.description.ilike(needle),
                Asset.keywords.ilike(needle),
                Asset.author.ilike(needle),
                Asset.topic.ilike(needle),
            )
        )
    if asset_type:
        stmt = stmt.where(Asset.asset_type.in_(asset_type))
    if expedition:
        stmt = stmt.where(Asset.expedition.in_(expedition))
    if station:
        stmt = stmt.where(Asset.station.in_(station))
    if topic:
        stmt = stmt.where(Asset.topic.in_(topic))
    if year:
        stmt = stmt.where(Asset.year.in_(year))
    if access_level:
        stmt = stmt.where(Asset.access_level.in_(access_level))
    return stmt


@router.get("/filters", response_model=FilterOptions)
def filter_options(db: Session = Depends(get_db)) -> FilterOptions:
    """Distinct values used to populate repository filter controls."""

    def distinct(column, cast=str):
        values = db.scalars(select(column).where(column.is_not(None)).distinct()).all()
        return sorted({cast(v) for v in values if v not in (None, "")})

    return FilterOptions(
        asset_types=list(ALLOWED_ASSET_TYPES),
        access_levels=list(ALLOWED_ACCESS_LEVELS),
        expeditions=distinct(Asset.expedition),
        stations=distinct(Asset.station),
        topics=distinct(Asset.topic),
        years=distinct(Asset.year, int),
    )


@router.get("/{asset_id}", response_model=AssetDetail)
def get_asset(asset_id: int, db: Session = Depends(get_db)) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return asset


@router.patch("/{asset_id}", response_model=AssetDetail)
def update_asset(asset_id: int, payload: AssetUpdate, db: Session = Depends(get_db)) -> Asset:
    """FR-04 metadata management."""
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")

    changes = payload.model_dump(exclude_unset=True)
    if "asset_type" in changes and changes["asset_type"] not in ALLOWED_ASSET_TYPES:
        changes["asset_type"] = "OTHER"
    if "access_level" in changes and changes["access_level"] not in ALLOWED_ACCESS_LEVELS:
        changes["access_level"] = "PUBLIC"
    if changes.get("title") is not None:
        changes["title"] = changes["title"].strip()
        if not changes["title"]:
            raise HTTPException(status_code=422, detail="title cannot be empty")

    for key, value in changes.items():
        if isinstance(value, str):
            value = value.strip() or None
            if key == "title" and value is None:
                continue
        setattr(asset, key, value)

    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, db: Session = Depends(get_db)) -> None:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    storage.delete_asset_dir(asset.id)
    db.delete(asset)
    db.commit()


@router.get("/{asset_id}/versions/{version_id}/download")
def download_version(asset_id: int, version_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """FR-14 — open the original stored source."""
    version = db.get(AssetVersion, version_id)
    if version is None or version.asset_id != asset_id:
        raise HTTPException(status_code=404, detail="version not found")
    try:
        path = storage.resolve_stored(version.file_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="stored path is invalid")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="stored file is missing")
    return FileResponse(
        path,
        filename=version.original_filename,
        media_type=version.mime_type or "application/octet-stream",
    )
