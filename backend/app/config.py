"""Runtime configuration, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def _b(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    app_name: str = "SupportPilot API"
    cors_origins: list[str] = field(default_factory=lambda: [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()])

    # Storage: "supabase" if SUPABASE_URL + key are set, else local SQLite.
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")
    sqlite_path: str = os.getenv("SQLITE_PATH", str(BACKEND_DIR / "data" / "supportpilot.db"))

    # Models
    category_model_path: str = os.getenv("CATEGORY_MODEL_PATH", str(BACKEND_DIR / "ml" / "models" / "category_classifier.joblib"))
    priority_model_path: str = os.getenv("PRIORITY_MODEL_PATH", str(BACKEND_DIR / "severity_priority" / "priority_model.joblib"))
    category_min_confidence: float = float(os.getenv("CATEGORY_MIN_CONFIDENCE", "0.40"))

    # Retrieval / RAG
    top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    chroma_path: str = os.getenv("SUPPORTPILOT_CHROMA_PATH", str(BACKEND_DIR / "semantic_search" / "chroma_db"))
    auto_resolve_min_confidence: float = float(os.getenv("AUTO_RESOLVE_MIN_CONFIDENCE", "0.50"))

    # Auth
    auth_secret: str = os.getenv("AUTH_SECRET", "")
    token_ttl_hours: int = int(os.getenv("TOKEN_TTL_HOURS", "12"))

    # Integrations ("mock" works offline; "real" needs credentials)
    jira_mode: str = os.getenv("JIRA_MODE", "mock").lower()
    jira_base_url: str = os.getenv("JIRA_BASE_URL", "")
    jira_email: str = os.getenv("JIRA_EMAIL", "")
    jira_api_token: str = os.getenv("JIRA_API_TOKEN", "")
    jira_project_key: str = os.getenv("JIRA_PROJECT_KEY", "SUP")

    email_mode: str = os.getenv("EMAIL_MODE", "mock").lower()  # mock | smtp
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    email_from: str = os.getenv("EMAIL_FROM", "supportpilot@example.com")


settings = Settings()
if not settings.auth_secret:
    import secrets as _s

    settings.auth_secret = _s.token_urlsafe(48)
    print("[auth] AUTH_SECRET is not set: using a random secret for this run. Everyone is signed out on restart. Set AUTH_SECRET in .env.")
