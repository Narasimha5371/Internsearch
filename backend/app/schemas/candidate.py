from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    school_name: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    url: HttpUrl | None = None
    highlights: list[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    github_url: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None
    website_url: HttpUrl | None = None
    skills: list[str] = Field(default_factory=list)
    education_history: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
