from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = Field(default="BANKNIFTY Analyst API", alias="APP_NAME")
    api_v1_prefix: str = Field(default="/api", alias="API_V1_PREFIX")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/banknifty_analyst",
        alias="DATABASE_URL",
    )
    use_sqlite_fallback: bool = Field(default=True, alias="USE_SQLITE_FALLBACK")
    zerodha_api_key: str = Field(default="", alias="ZERODHA_API_KEY")
    zerodha_api_secret: str = Field(default="", alias="ZERODHA_API_SECRET")
    zerodha_access_token: str = Field(default="", alias="ZERODHA_ACCESS_TOKEN")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

