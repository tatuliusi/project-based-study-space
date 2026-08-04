from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "semantic_memories"

    postgres_dsn: str = (
        "postgresql+asyncpg://memory:memory@localhost:5432/memoryengine"
    )

    consolidation_cron: str = "0 2 * * *"

    semantic_similarity_weight: float = 0.5
    recency_weight: float = 0.3
    importance_weight: float = 0.2
    recency_half_life_days: float = 7.0
    top_k_memories: int = 5


settings = Settings()
