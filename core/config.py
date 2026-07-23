"""Application settings, loaded from environment / .env (see .env.example)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SellerHelper"

    # Storage. Defaults to a local SQLite file (zero setup); point at Postgres by
    # setting DATABASE_URL to e.g. postgresql+psycopg://user:pass@host/db.
    database_url: str = "sqlite:///sellerhelper.db"
    redis_url: str = "redis://localhost:6381/0"

    # LLM — bring your own key in the open-source build. With no key the
    # explanation layer falls back to a deterministic template, so the tool runs
    # fully offline. Point llm_model at a cheaper model (e.g. claude-haiku-4-5)
    # to cut per-explanation cost.
    llm_api_key: str = ""
    llm_model: str = "claude-opus-4-8"

    # Wildberries collectors.
    wb_proxy_url: str = ""
    wb_requests_per_second: float = 0.5
    wb_search_version: str = "v9"
    wb_dest: int = -1257786
    wb_headless: bool = True  # run the Selenium spider without a visible window


@lru_cache
def get_settings() -> Settings:
    return Settings()
