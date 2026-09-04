from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    database_url: str = "postgresql+asyncpg://swarm:swarm@localhost:5432/reasoning_swarm"
    embedding_model: str = "text-embedding-3-small"
    reasoning_model: str = "gpt-4o-mini"
    max_rounds: int = 3
    consensus_threshold: float = 0.75

    class Config:
        env_file = ".env"


settings = Settings()
