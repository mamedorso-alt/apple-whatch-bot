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
    openai_vision_model: str = "gpt-4o-mini"
    openai_timeout_sec: float = 90.0
    smart_alerts_enabled: bool = True
    insights_baseline_days: int = 28
    insights_regularity_days: int = 14

    reels_agent_enabled: bool = False
    reels_agent_telegram_user_ids: str = ""
    reels_agent_daily_hour: int = 10
    reels_agent_daily_minute: int = 0
    reels_agent_timezone: str = ""
    reels_agent_anthropic_timeout_sec: int = 120
    reels_agent_anthropic_max_tokens: int = 2500
    # Wider window so a scheduled tick is likely to hit the reels send time (independent of morning reports).
    reels_agent_send_window_minutes: int = 120

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
