"""Configuration and settings for Sherlock Holmes AI."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="SHERLOCK_", env_file=".env")

    # API Keys
    anthropic_api_key: str = ""

    # Model settings
    model: str = "claude-sonnet-4-20250514"
    deep_model: str = "claude-opus-4-6"
    max_tokens: int = 4096

    # Paths
    cache_dir: Path = Path(".sherlock_cache")
    output_dir: Path = Path("sherlock/outputs")
    db_path: Path = Path(".sherlock_cache/investigations.db")

    # Agent settings
    max_web_results: int = 10
    max_scrape_depth: int = 2
    request_timeout: int = 30
    max_concurrent_requests: int = 5

    # Report settings
    include_evidence_appendix: bool = True
    report_format: str = "markdown"  # markdown, json, html

    # Telegram settings
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_enabled: bool = False

    @property
    def telegram_configured(self) -> bool:
        """Check if Telegram credentials are present."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
