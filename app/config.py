from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_user_ids: str = Field(
        default="",
        alias="TELEGRAM_ALLOWED_USER_IDS",
    )

    onec_base_url: str = Field(..., alias="ONEC_BASE_URL")
    onec_api_path: str = Field(..., alias="ONEC_API_PATH")
    onec_username: str = Field(..., alias="ONEC_USERNAME")
    onec_password: str = Field(..., alias="ONEC_PASSWORD")
    onec_timeout: float = Field(default=20.0, alias="ONEC_TIMEOUT")
    default_limit: int = Field(default=10, alias="DEFAULT_LIMIT")

    @field_validator("telegram_allowed_user_ids", mode="before")
    @classmethod
    def strip_ids(cls, v: str) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @property
    def allowed_user_ids(self) -> set[int]:
        if not self.telegram_allowed_user_ids:
            return set()
        parts = self.telegram_allowed_user_ids.replace(" ", "").split(",")
        return {int(x) for x in parts if x.isdigit()}

    @property
    def onec_root_url(self) -> str:
        base = self.onec_base_url.rstrip("/")
        path = self.onec_api_path.strip()
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
