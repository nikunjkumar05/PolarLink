from __future__ import annotations

import json
import logging
import re

from ..config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You write outreach summaries about polar research for a general audience. "
    "You are given numbered claims, each already supported by a quoted source passage. "
    "Rewrite them as flowing prose of at most 180 words. Never introduce a fact, number "
    "or comparison that is not present in the supplied claims and quotes. "
    "Do not add headings, bullet points, citations, or any text other than the prose body."
)


def llm_available() -> bool:
    return bool(LLM_API_KEY)


def llm_note() -> str | None:
    if llm_available():
        return None
    return "No POLARLINK_LLM_KEY set — composed extractively from the cited passages."


def _sentinel(index: int) -> str:
    return f"<<C{index:02d}>>"


def _strip_sentinels(text: str) -> str:
    text = re.sub(r"<<\s*C\d{2}\s*>>", "", text)
    text = re.sub(r"\[\s*C\d{2}\s*\]", "", text)
    text = re.sub(r"\(C\d{2}\)", "", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def build_prompt(claims: list[dict]) -> str:
    blocks = []
    for index, claim in enumerate(claims, start=1):
        quotes = "\n".join(f"    - {quote}" for quote in claim["quotes"][:2])
        blocks.append(
            f"{_sentinel(index)} CLAIM: {claim['text']}\n  SOURCE PASSAGES:\n{quotes}"
        )
    return (
        "Rewrite the following claims into one short outreach paragraph.\n\n"
        + "\n\n".join(blocks)
        + "\n\nPlace "
        + ", ".join(_sentinel(i) for i in range(1, len(claims) + 1))
        + " at the end of the sentence that uses the claim, then write nothing after the last sentinel."
    )


def draft_with_llm(claims: list[dict]) -> tuple[str, str, str]:
    """FR-17 — optional LLM pass.

    Returns (body, model, note). Raises RuntimeError when the model is
    unavailable or returns something unusable, so the caller can fall back to
    the extractive composer instead of losing the draft.
    """
    if not llm_available():
        raise RuntimeError("no LLM key configured")
    if not claims:
        raise RuntimeError("nothing to draft")

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(claims)},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }
    try:
        import requests

        response = requests.post(
            f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=LLM_TIMEOUT,
        )
        response.raise_for_status()
        body = json.loads(response.text)
        content = body["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 - any provider problem falls back
        log.warning("LLM drafting failed (%s); using extractive composition", exc)
        raise RuntimeError(f"LLM drafting failed: {type(exc).__name__}") from exc

    cleaned = _strip_sentinels(content or "")
    cleaned = re.sub(r"^#+\s*", "", cleaned).strip()
    if len(cleaned) < 80:
        raise RuntimeError("LLM returned too little usable text")
    return cleaned, LLM_MODEL, "Drafted by an LLM and checked against its cited passages."


def compose_extractive(title: str, claims: list[dict], summary: str | None = None) -> str:
    """FR-17 fallback — prose built only from verified source text.

    Every sentence is a source sentence, so the article can never state
    anything the archive does not already say.
    """
    paragraphs: list[str] = [f"# {title}"]
    if summary:
        paragraphs.append(summary)

    for index, claim in enumerate(claims, start=1):
        quote = (claim["quotes"] or [""])[0]
        sentence = _first_sentences(quote, limit=2)
        citation = f" [{_sentinel(index)}]"
        paragraphs.append(f"{sentence}{citation}".strip())

    paragraphs.append(
        "Every statement above is quoted from the linked PolarLink source passage; "
        "open the citation to see the original page."
    )
    return "\n\n".join(paragraphs)


def _first_sentences(text: str, limit: int = 2) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", compact)
    return " ".join(parts[:limit]).strip()


__all__ = ["build_prompt", "compose_extractive", "draft_with_llm", "llm_available", "llm_note"]