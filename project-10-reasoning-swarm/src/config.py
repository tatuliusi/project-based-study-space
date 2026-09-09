from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str
    database_url: str = "postgresql+asyncpg://swarm:swarm@localhost:5432/reasoning_swarm"
    embedding_model: str = "text-embedding-3-small"
    reasoning_model: str = "gpt-4o-mini"
    max_rounds: int = 3
    consensus_threshold: float = 0.75


settings = Settings()
