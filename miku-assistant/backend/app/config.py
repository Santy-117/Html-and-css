from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
MEMORIES_DIR = DATA_DIR / "memories"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
CACHE_DIR = DATA_DIR / "cache"
ALLOWLIST_PATH = BACKEND_DIR / "app" / "tools" / "allowlist.yaml"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "text-embedding-004"

    host: str = "127.0.0.1"
    port: int = 8765

    cache_ttl_seconds: int = 1800

    assistant_name: str = "Miku"


settings = Settings()

for path in (MEMORIES_DIR, VECTOR_STORE_DIR, CACHE_DIR):
    path.mkdir(parents=True, exist_ok=True)
