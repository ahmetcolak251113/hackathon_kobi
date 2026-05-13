from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Mock Cargo API", env="APP_NAME")
    debug: bool = Field(default=True, env="DEBUG")
    database_url: str = Field(
        default="sqlite:///./mock_cargo.db",
        env="DATABASE_URL",
    )
    delay_probability: float = Field(default=0.35, ge=0.0, le=1.0, env="DELAY_PROBABILITY")
    min_delay_seconds: int = Field(default=40, ge=1, env="MIN_DELAY_SECONDS")
    max_delay_seconds: int = Field(default=120, ge=1, env="MAX_DELAY_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
