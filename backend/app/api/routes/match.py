import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, get_current_user
from app.db.deps import get_db
from app.db.models import ParsedResume, ScrapedJob
from app.schemas.candidate import CandidateProfile
from app.schemas.job import JobListing
from app.schemas.match import MatchRequest, MatchResult
from app.services.users import get_or_create_user
from app.services.matchmaker import score_match

router = APIRouter(prefix="/match", tags=["match"])


@router.post("", response_model=MatchResult)
async def match_candidate(
    request: MatchRequest,
    _current_user: CurrentUser = Depends(get_current_user),
):
    return await score_match(request.candidate, request.job)


@router.get("/job/{job_id}", response_model=MatchResult)
async def match_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = get_or_create_user(db, current_user.user_id, current_user.email)
    resume = (
        db.query(ParsedResume)
        .filter(ParsedResume.user_id == user.id)
        .order_by(ParsedResume.created_at.desc())
        .first()
    )
    if not resume or not resume.parsed_json:
        raise HTTPException(status_code=404, detail="No parsed resume found.")

    job = db.query(ScrapedJob).filter(ScrapedJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    candidate = CandidateProfile.model_validate(resume.parsed_json)
    listing = JobListing(
        id=job.id,
        job_title=job.job_title,
        company=job.company,
        location=job.location,
        employment_type=job.employment_type,
        required_skills=job.required_skills or [],
        description=job.description,
        application_url=job.application_url,
        source=job.source,
        source_job_id=job.source_job_id,
        posted_date=job.posted_date.isoformat() if job.posted_date else None,
    )

    return await score_match(candidate, listing)
