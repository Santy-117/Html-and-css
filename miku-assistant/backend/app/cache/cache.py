"""Caché agresivo de respuestas para que las preguntas repetidas o muy
parecidas respondan al instante, sin llamar de nuevo a Gemini.

Estrategia: se normaliza el texto de entrada (minúsculas, sin espacios extra,
sin tildes) y se hashea junto con la clave de contexto (por ejemplo, si hay
resultados de RAG relevantes, para no servir una respuesta vieja cuando el
contexto cambió). Persiste en disco como JSON simple, así sobrevive a
reinicios del servicio.
"""

from __future__ import annotations

import hashlib
import json
import time
import unicodedata
from pathlib import Path

from app.config import CACHE_DIR, settings

_CACHE_FILE = CACHE_DIR / "response_cache.json"


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return " ".join(text.split())


def _make_key(user_message: str, context_fingerprint: str = "") -> str:
    raw = f"{_normalize(user_message)}|{context_fingerprint}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load() -> dict:
    if not _CACHE_FILE.exists():
        return {}
    try:
        return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    _CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_cached(user_message: str, context_fingerprint: str = "") -> str | None:
    key = _make_key(user_message, context_fingerprint)
    data = _load()
    entry = data.get(key)
    if entry is None:
        return None
    if time.time() - entry["ts"] > settings.cache_ttl_seconds:
        return None
    return entry["response"]


def set_cached(user_message: str, response: str, context_fingerprint: str = "") -> None:
    key = _make_key(user_message, context_fingerprint)
    data = _load()
    data[key] = {"response": response, "ts": time.time()}

    # Poda simple: si crece demasiado, se descartan las entradas más viejas.
    if len(data) > 500:
        newest = sorted(data.items(), key=lambda kv: kv[1]["ts"], reverse=True)[:400]
        data = dict(newest)

    _save(data)
