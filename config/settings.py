"""
Configuración central del sistema de monitoreo de precios.
Utiliza Pydantic Settings para tipado y validación.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ─── Rutas base ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
DB_DIR = BASE_DIR / "database"

LOGS_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Configuración global de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Base de datos ──────────────────────────────────────────────────────────
    database_url: str = f"sqlite:///{DB_DIR / 'monitor.db'}"

    # ── API ────────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # ── Scraper ────────────────────────────────────────────────────────────────
    scraper_timeout: int = 30_000          # ms
    scraper_retries: int = 3
    scraper_retry_delay: int = 5           # segundos
    scraper_headless: bool = True
    scraper_slow_mo: int = 0

    # ── Scheduler ─────────────────────────────────────────────────────────────
    default_frequency_minutes: int = 60
    max_retries: int = 3

    # ── Notificaciones: Telegram ───────────────────────────────────────────────
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_enabled: bool = False

    # ── Notificaciones: SMTP ───────────────────────────────────────────────────
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_to: Optional[str] = None
    smtp_enabled: bool = False

    # ── Notificaciones: Discord ────────────────────────────────────────────────
    discord_webhook_url: Optional[str] = None
    discord_enabled: bool = False

    # ── Logging ────────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_file: str = str(LOGS_DIR / "monitor.log")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valida que el nivel de log sea válido."""
        level = v.upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in valid:
            raise ValueError(f"log_level debe ser uno de: {valid}")
        return level


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna la instancia singleton de configuración."""
    return Settings()


def configure_logging(settings: Optional[Settings] = None) -> None:
    """Configura el sistema de logging de la aplicación."""
    if settings is None:
        settings = get_settings()

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(settings.log_file, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )

    # Silenciar librerías ruidosas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
