import uuid

from pydantic import BaseModel, ConfigDict, Field


class AutopilotSettingsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    auto_submit: bool = False
    paid_only: bool = True
    legit_only: bool = True
    max_applications_per_day: int = Field(default=5, ge=1, le=50)
    limit_per_company: int = Field(default=25, ge=1, le=200)
    greenhouse_companies: list[str] = Field(default_factory=list)
    lever_companies: list[str] = Field(default_factory=list)
    title_keywords: list[str] = Field(default_factory=lambda: ["intern"])


class AutopilotSettingsUpdate(AutopilotSettingsBase):
    pass


class AutopilotSettingsRead(AutopilotSettingsBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: str
    updated_at: str


class AutopilotRunLogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    user_id: uuid.UUID
    trigger: str
    status: str
    jobs_seen: int
    jobs_qualified: int
    applications_queued: int
    message: str | None = None
    details_json: dict | None = None
    started_at: str
    completed_at: str | None = None


class AutopilotRunNowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    status: str
