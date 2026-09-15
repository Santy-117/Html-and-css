from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str


class ChatResponse(BaseModel):
    reply: str
    cached: bool = False


class ReindexResponse(BaseModel):
    chunks_indexed: int
