from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    app_base_url: str = "http://localhost:8000"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/productivity"
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    jwt_secret: str = ""
    default_timezone: str = "Asia/Baku"
    morning_send_hour: int = 8
    morning_send_minute: int = 30
    evening_send_hour: int = 20
    evening_send_minute: int = 30
    link_code_ttl_min: int = 15
    scheduler_enabled: bool = False
    scheduler_interval_min: int = 30
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"
    anthropic_timeout_sec: int = 20
    ai_coach_context_days: int = 7
    openai_api_key: str = ""
    openai_stt_model: str = "whisper-1"
    openai_stt_timeout_sec: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
