from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.db.models import ScrapedJob
from app.schemas.job import JobListing


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def upsert_jobs(db: Session, jobs: list[JobListing]) -> tuple[int, int]:
    inserted = 0
    updated = 0

    for job in jobs:
        existing = None
        if job.source_job_id:
            existing = (
                db.query(ScrapedJob)
                .filter(
                    ScrapedJob.source == job.source,
                    ScrapedJob.source_job_id == job.source_job_id,
                )
                .first()
            )

        if existing is None:
            existing = (
                db.query(ScrapedJob)
                .filter(ScrapedJob.application_url == str(job.application_url))
                .first()
            )

        posted_date = _parse_date(job.posted_date)

        if existing:
            existing.job_title = job.job_title
            existing.company = job.company
            existing.location = job.location
            existing.employment_type = job.employment_type
            existing.description = job.description
            existing.required_skills = job.required_skills
            existing.application_url = str(job.application_url)
            existing.posted_date = posted_date
            db.add(existing)
            updated += 1
        else:
            db.add(
                ScrapedJob(
                    source=job.source,
                    source_job_id=job.source_job_id,
                    job_title=job.job_title,
                    company=job.company,
                    location=job.location,
                    employment_type=job.employment_type,
                    description=job.description,
                    required_skills=job.required_skills,
                    application_url=str(job.application_url),
                    posted_date=posted_date,
                )
            )
            inserted += 1

    db.commit()
    return inserted, updated
