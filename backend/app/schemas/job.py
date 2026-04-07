import uuid

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class JobListing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    job_title: str
    company: str
    location: str | None = None
    employment_type: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    description: str | None = None
    application_url: HttpUrl
    source: str
    source_job_id: str | None = None
    posted_date: str | None = None
    is_internship: bool = True
    is_paid: bool | None = None
    is_legit: bool = True
    requires_candidate_payment: bool = False
    compensation_summary: str | None = None
    safety_notes: list[str] = Field(default_factory=list)


class JobScrapeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    greenhouse_companies: list[str] = Field(default_factory=list)
    lever_companies: list[str] = Field(default_factory=list)
    title_keywords: list[str] = Field(default_factory=lambda: ["intern"])
    limit_per_company: int = Field(default=50, ge=1, le=200)


class JobScrapeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inserted: int
    updated: int
    total_seen: int
