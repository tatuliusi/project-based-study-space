from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    judge_model: str = "gpt-4o"
    app_model: str = "gpt-4o-mini"

    postgres_dsn: str = "postgresql+asyncpg://eval:eval@localhost:5432/evaldb"

    regression_threshold: float = 0.05
    absolute_floor_correctness: float = 0.7
    sample_repeats: int = 3


settings = Settings()
