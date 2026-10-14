"""
Centralized application configuration.

All configuration is environment-driven (12-factor app). Nothing is
hardcoded so the same image can run in dev / staging / prod by only
changing env vars (see .env.example).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "Lumen API"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Security ---
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    ALGORITHM: str = "HS256"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./lumen.db"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Storage ---
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_MB: int = 25
    VECTOR_INDEX_DIR: str = "./storage/vector_indexes"

    # --- AI / LLM ---
    LLM_PROVIDER: str = "openai"  # openai | none (falls back to extractive mode)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""  # leave empty for OpenAI itself; set to point at
    # any other OpenAI-compatible endpoint (e.g. Groq's free tier:
    # https://api.groq.com/openai/v1)
    OPENAI_CHAT_MODEL: str = "gpt-5.6-terra"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # --- RAG tuning ---
    CHUNK_SIZE_TOKENS: int = 400
    CHUNK_OVERLAP_TOKENS: int = 60
    TOP_K_RETRIEVAL: int = 6

    # --- Spaced repetition (SM-2) ---
    SM2_MIN_EASE_FACTOR: float = 1.3
    SM2_DEFAULT_EASE_FACTOR: float = 2.5


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — avoids re-parsing env on every request."""
    settings = Settings()
    # Never sign tokens with the placeholder key: it is public, so anyone could
    # forge a login with it (and ENV defaults to "development", so a deploy
    # that forgets to set ENV would otherwise use it). Use a random per-process
    # key instead (users re-login after a restart) and say so loudly.
    if settings.SECRET_KEY.startswith("change-me"):
        import logging, secrets
        settings.SECRET_KEY = secrets.token_hex(32)
        logging.getLogger(__name__).warning(
            "SECRET_KEY is not set — using a random key for this process. "
            "Set SECRET_KEY so logins survive restarts.")
    return settings