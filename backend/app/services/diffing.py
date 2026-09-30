from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import EvidencePassage

# Two passages are "the same passage, edited" when they sit at the same spot in
# the document and share enough wording. Everything else counts as added/removed.
_SIMILARITY_THRESHOLD = 0.55


@dataclass(slots=True)
class PassageChange:
    kind: str  # ADDED | REMOVED | MODIFIED
    previous: EvidencePassage | None = None
    current: EvidencePassage | None = None
    similarity: float | None = None

    @property
    def previous_id(self) -> int | None:
        return self.previous.id if self.previous is not None else None

    @property
    def current_id(self) -> int | None:
        return self.current.id if self.current is not None else None


@dataclass(slots=True)
class DiffResult:
    changes: list[PassageChange] = field(default_factory=list)

    @property
    def added(self) -> int:
        return sum(1 for c in self.changes if c.kind == "ADDED")

    @property
    def removed(self) -> int:
        return sum(1 for c in self.changes if c.kind == "REMOVED")

    @property
    def modified(self) -> int:
        return sum(1 for c in self.changes if c.kind == "MODIFIED")

    @property
    def touched(self) -> list[PassageChange]:
        return [c for c in self.changes if c.kind in {"MODIFIED", "REMOVED"}]


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def similarity(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 1.0 if left.strip() == right.strip() else 0.0
    return len(a & b) / len(a | b)


def diff_passages(
    previous: list[EvidencePassage], current: list[EvidencePassage]
) -> DiffResult:
    """FR-31 — line up two versions' passages and report what moved.

    Alignment is positional first (a re-uploaded report keeps its page and
    sequence order), with a token-overlap fallback so an inserted paragraph
    does not make every following passage look changed.
    """
    result = DiffResult()
    old_by_page: dict[tuple[int | None, int], EvidencePassage] = {
        (p.page_number, p.sequence_number): p for p in previous
    }
    used: set[int] = set()

    for passage in current:
        match = old_by_page.get((passage.page_number, passage.sequence_number))
        if match is None or match.id in used:
            match = _best_unused(passage, previous, used)
        if match is None:
            result.changes.append(PassageChange(kind="ADDED", current=passage))
            continue

        used.add(match.id)
        score = similarity(match.content, passage.content)
        if score >= _SIMILARITY_THRESHOLD:
            result.changes.append(
                PassageChange(kind="MODIFIED", previous=match, current=passage, similarity=score)
            )
        else:
            result.changes.append(PassageChange(kind="ADDED", current=passage))
            result.changes.append(PassageChange(kind="REMOVED", previous=match))

    for passage in previous:
        if passage.id not in used:
            result.changes.append(PassageChange(kind="REMOVED", previous=passage))

    result.changes.sort(key=lambda c: (c.current or c.previous).sequence_number)
    return result


def _best_unused(
    candidate: EvidencePassage, previous: list[EvidencePassage], used: set[int]
) -> EvidencePassage | None:
    best: tuple[float, EvidencePassage] | None = None
    for passage in previous:
        if passage.id in used:
            continue
        score = similarity(passage.content, candidate.content)
        if best is None or score > best[0]:
            best = (score, passage)
    return best[1] if best and best[0] >= _SIMILARITY_THRESHOLD else None


def _digest(changes: list[PassageChange]) -> str:
    parts = []
    for change in changes:
        if change.kind == "MODIFIED":
            parts.append(f"M:{change.previous_id}->{change.current_id}")
        elif change.kind == "REMOVED":
            parts.append(f"R:{change.previous_id}")
        else:
            parts.append(f"A:{change.current_id}")
    return ",".join(sorted(parts))


def changes_digest(changes: list[PassageChange]) -> str:
    """Stable fingerprint of a diff, stored on the impact alert."""
    return _digest(changes)


__all__ = [
    "DiffResult",
    "PassageChange",
    "changes_digest",
    "diff_passages",
    "similarity",
]