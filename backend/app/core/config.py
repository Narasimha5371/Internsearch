from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+pysqlite:///./job_agent.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "memory://"
    celery_result_backend: str = "cache+memory://"
    celery_task_always_eager: bool = True
    celery_task_eager_propagates: bool = False

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
    allowed_application_host_suffixes: list[str] = ["greenhouse.io", "lever.co"]
    store_resume_raw_text: bool = False

    resume_upload_rate_limit_count: int = 12
    resume_upload_rate_limit_window_seconds: int = 3600
    jobs_scrape_rate_limit_count: int = 20
    jobs_scrape_rate_limit_window_seconds: int = 3600
    applications_submit_rate_limit_count: int = 20
    applications_submit_rate_limit_window_seconds: int = 3600
    autopilot_run_now_rate_limit_count: int = 6
    autopilot_run_now_rate_limit_window_seconds: int = 3600

    cors_allow_origins: list[str] = ["http://localhost:3000"]

    clerk_jwks_url: str | None = None
    clerk_issuer: str | None = None
    clerk_audience: str | None = None
    support_email: str | None = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_prefix="",
        case_sensitive=False,
    )


settings = Settings()
