"""Almacén local de vectores para el RAG (sin dependencias pesadas tipo
faiss/chromadb: para el volumen de un puñado de documentos markdown personales,
numpy + un JSON de metadatos es suficiente y no requiere instalar nada extra)."""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from app.config import VECTOR_STORE_DIR

_VECTORS_FILE = VECTOR_STORE_DIR / "vectors.npy"
_META_FILE = VECTOR_STORE_DIR / "meta.json"


@dataclass(frozen=True)
class Chunk:
    text: str
    source: str


def save_index(chunks: list[Chunk], vectors: np.ndarray) -> None:
    np.save(_VECTORS_FILE, vectors)
    meta = [{"text": c.text, "source": c.source} for c in chunks]
    _META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index() -> tuple[list[Chunk], np.ndarray] | None:
    if not _VECTORS_FILE.exists() or not _META_FILE.exists():
        return None
    vectors = np.load(_VECTORS_FILE)
    meta = json.loads(_META_FILE.read_text(encoding="utf-8"))
    chunks = [Chunk(text=m["text"], source=m["source"]) for m in meta]
    return chunks, vectors
