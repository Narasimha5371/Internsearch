from pydantic import BaseModel, ConfigDict, Field

from app.schemas.candidate import CandidateProfile
from app.schemas.job import JobListing


class MatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: CandidateProfile
    job: JobListing


class MatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_score: int = Field(ge=0, le=100)
    reasoning: str
