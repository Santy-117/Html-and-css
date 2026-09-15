"""Historial de conversación en memoria, por sesión.

Simple a propósito: el display (Vue/Electron) es un solo usuario local, así
que no hace falta una base de datos. Si el proceso se reinicia se pierde el
historial de la sesión actual, pero el RAG (memorias en markdown) y el caché
en disco persisten igual.
"""

from __future__ import annotations

from app.llm.gemini_client import ChatTurn

_MAX_TURNS_KEPT = 20

_sessions: dict[str, list[ChatTurn]] = {}


def get_history(session_id: str) -> list[ChatTurn]:
    return _sessions.get(session_id, [])


def set_history(session_id: str, history: list[ChatTurn]) -> None:
    _sessions[session_id] = history[-_MAX_TURNS_KEPT:]
