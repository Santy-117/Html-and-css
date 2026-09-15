"""Punto de entrada del motor cognitivo de Miku.

Corre localmente (sin exponerse a internet) como un servicio HTTP que el
display en Vue + Three.js (dentro de Electron) consume. Flujo por mensaje:

1. Se revisa el caché agresivo (si es una pregunta repetida, se responde al
   instante sin tocar la red).
2. Se hace RAG sobre tus documentos markdown para traer contexto relevante.
3. Se llama a Gemini con ese contexto y las tools con allowlist habilitadas.
4. La respuesta final se guarda en caché e historial, y se devuelve.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas import ChatRequest, ChatResponse, ReindexResponse
from app.api.sessions import get_history, set_history
from app.cache.cache import get_cached, set_cached
from app.config import settings
from app.llm.gemini_client import generate_reply
from app.rag.indexer import rebuild_index
from app.rag.retriever import build_context_block

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("miku")

app = FastAPI(title="Miku - Motor Cognitivo", version="0.1.0")

# El display corre embebido en Electron (origen local), pero se deja CORS
# abierto a localhost para facilitar desarrollo con `vite` en paralelo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "assistant": settings.assistant_name}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje está vacío.")

    rag_context, fingerprint = build_context_block(message)

    cached = get_cached(message, fingerprint)
    if cached is not None:
        logger.info("cache hit para sesión %s", request.session_id)
        return ChatResponse(reply=cached, cached=True)

    history = get_history(request.session_id)
    try:
        result = generate_reply(history, message, rag_context)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    set_history(request.session_id, result.history)
    set_cached(message, result.text, fingerprint)

    return ChatResponse(reply=result.text, cached=False)


@app.post("/rag/reindex", response_model=ReindexResponse)
def reindex() -> ReindexResponse:
    try:
        count = rebuild_index()
    except Exception as exc:  # noqa: BLE001 - se reporta tal cual al cliente local
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ReindexResponse(chunks_indexed=count)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
