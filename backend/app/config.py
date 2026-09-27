from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "sqlite+aiosqlite:///./kidsedu.db"

    telegram_bot_token: str = ""
    gemini_api_key: str = ""

    video_storage_path: str = "./storage/videos"
    tts_cache_path: str = "./storage/tts_cache"

    ingestor_interval_hours: int = 12

    # Общий пароль родительской панели (frontend-admin). Пустая строка
    # отключает проверку — удобно для локальной разработки, но ОБЯЗАТЕЛЬНО
    # должен быть задан в проде (см. CLAUDE.md).
    admin_dashboard_password: str = ""


settings = Settings()
