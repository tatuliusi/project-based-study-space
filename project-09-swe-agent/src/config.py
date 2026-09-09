from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    github_token: str = ""
    database_url: str = "postgresql://swe:swe@localhost:5432/swe_agent"

    docker_image: str = "python:3.11-slim"
    max_iterations: int = 5
    sandbox_memory_limit: str = "512m"
    sandbox_cpu_quota: int = 50000
    command_timeout: int = 60

    repo_map_depth: int = 3
    repo_map_max_tokens: int = 2000
    large_file_threshold_bytes: int = 5120

    allowed_commands: list[str] = [
        "pytest",
        "python",
        "pip",
        "pip3",
        "python3",
        "ls",
        "cat",
        "find",
        "grep",
        "head",
        "wc",
    ]


settings = Settings()
