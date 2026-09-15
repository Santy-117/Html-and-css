"""Indexado: lee los .md de data/memories, los divide en chunks y pide sus
embeddings a Gemini para guardarlos en el store local."""

from __future__ import annotations

import numpy as np
from google import genai

from app.config import MEMORIES_DIR, settings
from app.rag.store import Chunk, save_index

_MAX_CHARS_PER_CHUNK = 800
_OVERLAP_CHARS = 120


def _split_into_chunks(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= _MAX_CHARS_PER_CHUNK:
            current = f"{current}\n\n{para}" if current else para
            continue

        if current:
            chunks.append(current)
        if len(para) <= _MAX_CHARS_PER_CHUNK:
            current = para
        else:
            for i in range(0, len(para), _MAX_CHARS_PER_CHUNK - _OVERLAP_CHARS):
                chunks.append(para[i : i + _MAX_CHARS_PER_CHUNK])
            current = ""

    if current:
        chunks.append(current)
    return chunks


def _read_memory_files() -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(MEMORIES_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for piece in _split_into_chunks(text):
            chunks.append(Chunk(text=piece, source=path.name))
    return chunks


def rebuild_index() -> int:
    """Reconstruye el índice RAG completo. Devuelve la cantidad de chunks
    indexados. Requiere GEMINI_API_KEY configurada."""
    chunks = _read_memory_files()
    if not chunks:
        save_index([], np.zeros((0, 1), dtype=np.float32))
        return 0

    client = genai.Client(api_key=settings.gemini_api_key)
    result = client.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=[c.text for c in chunks],
    )
    vectors = np.array([e.values for e in result.embeddings], dtype=np.float32)
    save_index(chunks, vectors)
    return len(chunks)
