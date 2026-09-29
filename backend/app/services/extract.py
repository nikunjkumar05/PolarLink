from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".md", ".csv", ".tsv", ".json", ".log"}


@dataclass(slots=True)
class PageText:
    page_number: int | None
    text: str


@dataclass(slots=True)
class ExtractionResult:
    pages: list[PageText]
    warning: str | None = None


def extract(path: Path, mime_type: str | None, filename: str) -> ExtractionResult:
    """FR-06 — pull page-addressable text out of an uploaded source.

    Returns an empty result with a warning instead of raising, so a source we
    cannot parse still finishes as DONE and stays usable as a download.
    """
    suffix = Path(filename).suffix.lower()
    is_pdf = mime_type == "application/pdf" or suffix == ".pdf"
    is_text = mime_type in {"text/plain", "text/csv", "text/markdown", "application/json"} or (
        suffix in TEXT_SUFFIXES
    )

    if is_pdf:
        return _extract_pdf(path)
    if is_text:
        return _extract_text(path)
    return ExtractionResult(
        pages=[],
        warning=f"Text extraction is not implemented for {mime_type or suffix or 'this format'} yet.",
    )


def _extract_pdf(path: Path) -> ExtractionResult:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ExtractionResult(pages=[], warning="pypdf is not installed.")

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001 - a broken PDF must not block the upload
        return ExtractionResult(pages=[], warning=f"Could not read PDF: {exc}")

    pages: list[PageText] = []
    blank = 0
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            text = ""
        if not text.strip():
            blank += 1
        pages.append(PageText(page_number=index, text=text))

    warning = None
    if pages and blank == len(pages):
        warning = "No selectable text found — this PDF appears to be scanned. OCR is not wired up yet."
    elif blank:
        warning = f"{blank} of {len(pages)} pages had no selectable text (likely scanned)."
    return ExtractionResult(pages=pages, warning=warning)


def _extract_text(path: Path) -> ExtractionResult:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return ExtractionResult(pages=[], warning=f"Could not read file: {exc}")
    text = raw.decode("utf-8", errors="replace")
    return ExtractionResult(pages=[PageText(page_number=None, text=text)])


# ---------- chunking ----------

_PARAGRAPH = re.compile(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*")
_BLANK_LINE = re.compile(r"\n\s*\n")


@dataclass(slots=True)
class Chunk:
    text: str
    page_number: int | None
    start_offset: int
    end_offset: int


def chunk_pages(
    pages: list[PageText],
    target: int = 1400,
    overlap: int = 200,
) -> list[Chunk]:
    """FR-13 — split extracted text into evidence passages that keep their page
    and character offsets so a result can open the right location later."""
    chunks: list[Chunk] = []
    for page in pages:
        if not page.text or not page.text.strip():
            continue
        chunks.extend(chunk_page(page.text, page.page_number, target=target, overlap=overlap))
    return chunks


def chunk_page(
    raw: str,
    page_number: int | None,
    target: int = 1400,
    overlap: int = 200,
) -> list[Chunk]:
    paragraphs = [(m.start(), m.end()) for m in _PARAGRAPH.finditer(raw)]
    if not paragraphs:
        return []

    groups: list[tuple[int, int]] = []
    current: list[int] | None = None
    for start, end in paragraphs:
        if current is None:
            current = [start, end]
        elif end - current[0] <= target:
            current[1] = end
        else:
            groups.append((current[0], current[1]))
            current = [start, end]
    if current is not None:
        groups.append((current[0], current[1]))

    # Pull each group's start back so consecutive passages overlap slightly.
    overlapped: list[tuple[int, int]] = []
    for index, (start, end) in enumerate(groups):
        if index > 0:
            start = max(start - overlap, overlapped[-1][0] + 1)
        overlapped.append((start, end))

    spans: list[tuple[int, int]] = []
    max_span = int(target * 1.6)
    for start, end in overlapped:
        if end - start <= max_span:
            spans.append((start, end))
            continue
        position = start
        while True:
            stop = min(position + target, end)
            spans.append((position, stop))
            if stop >= end:
                break
            position = max(stop - overlap, position + 1)

    return [
        Chunk(text=raw[start:end], page_number=page_number, start_offset=start, end_offset=end)
        for start, end in spans
        if raw[start:end].strip()
    ]


def summarise(text: str, limit: int = 280) -> str:
    compact = _BLANK_LINE.sub(" ", text)
    compact = re.sub(r"\s+", " ", compact).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"
