from __future__ import annotations

import hashlib
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from ..config import STORAGE_DIR

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class StorageError(Exception):
    """Base class for storage failures that map to a client error."""


class EmptyUpload(StorageError):
    pass


class UploadTooLarge(StorageError):
    pass


def safe_filename(name: str) -> str:
    """Normalise an uploaded filename and strip any path components."""
    name = unicodedata.normalize("NFKC", name or "file")
    name = Path(name.replace("\\", "/")).name
    name = _SAFE_CHARS.sub("_", name).strip("._")
    return name[:200] or "file"


@dataclass(slots=True)
class StoredFile:
    relative_path: str
    absolute_path: Path
    file_hash: str
    size_bytes: int


def store_file(
    asset_id: int,
    version_number: int,
    filename: str,
    stream: BinaryIO,
    max_bytes: int | None = None,
) -> StoredFile:
    """Write the original upload to a persistent volume and fingerprint it (FR-30).

    The stream is copied verbatim; nothing about the original is rewritten.
    """
    name = safe_filename(filename)
    target_dir = STORAGE_DIR / f"assets/{asset_id:06d}/v{version_number}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / name

    digest = hashlib.sha256()
    size = 0
    try:
        with target.open("wb") as out:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if max_bytes is not None and size > max_bytes:
                    raise UploadTooLarge(f"file exceeds {max_bytes} bytes")
                digest.update(chunk)
                out.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise

    if size == 0:
        target.unlink(missing_ok=True)
        raise EmptyUpload("uploaded file is empty")

    relative = target.relative_to(STORAGE_DIR).as_posix()
    return StoredFile(
        relative_path=relative,
        absolute_path=target,
        file_hash=digest.hexdigest(),
        size_bytes=size,
    )


def resolve_stored(relative_path: str) -> Path:
    """Resolve a stored path, refusing anything that escapes STORAGE_DIR."""
    candidate = (STORAGE_DIR / relative_path).resolve()
    root = STORAGE_DIR.resolve()
    if root not in candidate.parents and candidate != root:
        raise ValueError("path escapes storage root")
    return candidate


def delete_asset_dir(asset_id: int) -> None:
    target = STORAGE_DIR / f"assets/{asset_id:06d}"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def sniff_mime(head: bytes, filename: str) -> str:
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[4:8] == b"ftyp":
        return "video/mp4"
    suffix = Path(filename).suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".mp4": "video/mp4",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".json": "application/json",
    }.get(suffix, "application/octet-stream")
