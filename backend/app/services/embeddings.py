from __future__ import annotations

import threading
from typing import Protocol, Sequence, runtime_checkable

import numpy as np

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
_BATCH = 64

_lock = threading.Lock()
_provider: "EmbeddingProvider | None" = None
_error: str | None = None


class EmbeddingUnavailable(RuntimeError):
    pass


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str
    dim: int

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]: ...


class FastEmbedProvider:
    """ONNX embeddings via fastembed — no torch, model cached on disk."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model)
        self.name = model
        probe = next(iter(self._model.embed(["dimension probe"])))
        self.dim = int(np.asarray(probe).shape[-1])

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        if not texts:
            return []
        with _lock:
            return [np.asarray(vector, dtype=np.float32) for vector in self._model.embed(list(texts))]


def get_provider() -> EmbeddingProvider | None:
    """Return the shared provider, loading it once. Never raises."""
    global _provider, _error
    with _lock:
        if _provider is None and _error is None:
            try:
                _provider = FastEmbedProvider()
            except Exception as exc:  # noqa: BLE001 - model/network failures must not break search
                _error = f"{type(exc).__name__}: {exc}"
    return _provider


def provider_error() -> str | None:
    get_provider()
    return _error


def reset_provider() -> None:
    """Testing helper — drop the cached provider and error."""
    global _provider, _error
    with _lock:
        _provider = None
        _error = None


def to_blob(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_blob(blob: bytes | None) -> np.ndarray | None:
    if not blob:
        return None
    array = np.frombuffer(blob, dtype=np.float32)
    return array if array.size else None
