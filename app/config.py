from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INSECURE_PLACEHOLDER = "change-this-to-a-strong-random-secret"


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 4

    secret_api_key: str = Field(default=INSECURE_PLACEHOLDER, min_length=16)

    verify_from_email: str = "verify@yourdomain.com"
    verify_ehlo_hostname: str = "verify.yourdomain.com"

    database_url: str = ""

    dns_cache_ttl: int = 3600
    smtp_cache_ttl: int = 86400

    rate_limit_verify: str = "30/minute"
    rate_limit_bulk: str = "5/minute"

    smtp_connect_timeout: float = 15.0
    smtp_command_timeout: float = 10.0
    smtp_overall_timeout: float = 30.0

    smtp_rate_gmail: int = 3
    smtp_rate_outlook: int = 5
    smtp_rate_yahoo: int = 3
    smtp_rate_default: int = 15

    smtp_max_concurrent: int = 20
    smtp_max_per_host: int = 3

    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    log_level: str = "INFO"

    bulk_max_size: int = 50

    model_config = {"env_file": ".env", "extra": "ignore", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_api_key(self) -> "Settings":
        if self.secret_api_key == INSECURE_PLACEHOLDER:
            logger.warning(
                "SECRET_API_KEY is set to the default placeholder. "
                "Please set a strong random key in your .env file."
            )
        return self

    @property
    def database_url_effective(self) -> str:
        if self.database_url:
            return self.database_url
        db_path = PROJECT_ROOT / "data" / "verifier.db"
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url_effective

    def get_smtp_rate_limit(self, domain: str) -> int:
        rate_map = {
            "gmail.com": self.smtp_rate_gmail,
            "googlemail.com": self.smtp_rate_gmail,
            "outlook.com": self.smtp_rate_outlook,
            "hotmail.com": self.smtp_rate_outlook,
            "live.com": self.smtp_rate_outlook,
            "yahoo.com": self.smtp_rate_yahoo,
            "yahoo.co.uk": self.smtp_rate_yahoo,
            "ymail.com": self.smtp_rate_yahoo,
        }
        return rate_map.get(domain, self.smtp_rate_default)


settings = Settings()
