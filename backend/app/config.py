"""Настройки приложения из переменных окружения."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- БД / инфраструктура ---
    database_url: str = "postgresql+psycopg://jailtracker:jailtracker@localhost:5432/jailtracker"
    redis_url: str = "redis://localhost:6379/0"

    # --- Безопасность ---
    # ВАЖНО: в проде задать через env. Дефолт пригоден только для локальной разработки.
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60 * 8

    # Список разрешённых origin'ов через запятую. Звёздочки по умолчанию НЕТ — security-фикс.
    cors_origins: str = "http://localhost:5173"

    # Ключ, которым симулятор/устройство-источник аутентифицируется на /api/ingest/location.
    # Реальные браслеты ходят через TCP gateway по IMEI.
    ingest_rate_limit_per_minute: int = 120

    # --- Сидирование демо-админа ---
    admin_email: str = "admin@jailtracker.kz"
    admin_password: str = "admin123"
    admin_full_name: str = "Администратор ИУ"

    # --- Redis-каналы ---
    events_channel: str = "jailtracker:events"
    device_cmd_prefix: str = "dev_cmd:"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
