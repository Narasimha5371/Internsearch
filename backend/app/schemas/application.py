import uuid

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ApplicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: uuid.UUID | None = None
    application_url: HttpUrl | None = None
    resume_file_path: str | None = None
    auto_submit: bool = False


class ApplicationEnqueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_id: uuid.UUID
    task_id: str
    status: str


class ApplicationLogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    status: str
    mode: str
    application_url: str | None = None
    job_id: uuid.UUID | None = None
    error_message: str | None = None
    created_at: str
    result_json: dict | None = None
