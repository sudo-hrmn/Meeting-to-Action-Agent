"""
Settings module — all configuration loaded from environment variables.

Why: Centralising config with Pydantic BaseSettings gives us:
  - Type-safe config values
  - Automatic .env loading
  - Fail-fast validation on startup if required vars are missing
  - Easy to mock in tests
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM API Keys ---
    groq_api_key: str
    tavily_api_key: str = ""
    huggingfacehub_api_token: str = ""

    # --- LangSmith Tracing ---
    langsmith_api_key: str = ""
    langchain_api_key: str = ""
    langsmith_tracing: str = "true"
    langsmith_project: str = "Meeting-to-Action-Agent"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # --- App Config ---
    app_name: str = "Meeting-to-Action Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./meeting_agent.db"
    database_path: str = "./meeting_agent.db"

    # --- LLM Config ---
    groq_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    # --- CORS ---
    allowed_origins: list[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]


@lru_cache()
def get_settings() -> Settings:
    """
    Return cached settings instance.

    Using lru_cache means the .env file is read exactly once per process,
    not on every request. Tests can clear the cache to inject different values.
    """
    return Settings()
