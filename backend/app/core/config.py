from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://job_agent:job_agent@localhost:5432/job_agent"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    llm_provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    groq_api_key: str | None = None
    groq_model: str = "llama3-8b-8192"

    resume_storage_dir: str = "storage/resumes"
    artifacts_dir: str = "artifacts"

    playwright_headless: bool = True
    playwright_test_url: str = "https://example.com"
    max_resume_size_mb: int = 8
    autopilot_cycle_minutes: int = 30

    cors_allow_origins: list[str] = ["http://localhost:3000"]

    clerk_jwks_url: str | None = None
    clerk_issuer: str | None = None
    support_email: str | None = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_prefix="",
        case_sensitive=False,
    )


settings = Settings()
