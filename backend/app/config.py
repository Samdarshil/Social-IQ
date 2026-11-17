"""Application settings. All secrets come from environment variables (never committed)."""
from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def _persisted_dev_secret(name: str, factory) -> str:
    """Dev-only convenience: generate a secret once and keep it in data/ (git-ignored).
    In production, set the env var explicitly; this fallback logs a warning."""
    path = DATA_DIR / f".{name}"
    if path.exists():
        return path.read_text().strip()
    value = factory()
    path.write_text(value)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    print(f"[socialiq] WARNING: {name.upper()} not set; generated a local dev secret at {path}. "
          f"Set it via environment in production.")
    return value


class Settings:
    def __init__(self) -> None:
        self.env = os.getenv("SOCIALIQ_ENV", "development")
        self.database_url = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'socialiq.db'}")
        self.jwt_secret = os.getenv("JWT_SECRET") or _persisted_dev_secret(
            "jwt_secret", lambda: secrets.token_urlsafe(48))
        self.token_encryption_key = os.getenv("TOKEN_ENCRYPTION_KEY") or _persisted_dev_secret(
            "token_key", lambda: Fernet.generate_key().decode())
        self.jwt_ttl_minutes = int(os.getenv("JWT_TTL_MINUTES", "720"))
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        self.cors_origins = [o.strip() for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
        # LLM (optional). Without a key the assistant runs in local-reasoning mode. Gemini powers the assistant.
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.gemini_base_url = os.getenv("GEMINI_BASE_URL", "")      # optional: proxy / local test server
        self.llm_timeout_s = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))        # per request
        self.llm_total_budget_s = float(os.getenv("LLM_TOTAL_BUDGET_SECONDS", "45"))  # whole question, all tool rounds
        # Platform OAuth credentials (all optional)
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.instagram_client_id = os.getenv("INSTAGRAM_CLIENT_ID", "")
        self.instagram_client_secret = os.getenv("INSTAGRAM_CLIENT_SECRET", "")
        self.x_client_id = os.getenv("X_CLIENT_ID", "")
        self.x_client_secret = os.getenv("X_CLIENT_SECRET", "")
        self.linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
        self.linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
