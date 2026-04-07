from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, get_current_user
from app.db.deps import get_db
from app.db.models import ScrapedJob
from app.schemas.job import JobListing, JobScrapeRequest, JobScrapeResult
from app.services.job_policy import analyze_job
from app.services.job_scrapers import fetch_greenhouse_jobs, fetch_lever_jobs
from app.services.job_store import upsert_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_listing(job: ScrapedJob) -> JobListing:
    policy = analyze_job(
        title=job.job_title,
        description=job.description,
        employment_type=job.employment_type,
        application_url=job.application_url,
    )
    return JobListing(
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
        is_internship=policy.is_internship,
        is_paid=policy.is_paid,
        is_legit=policy.is_legit,
        requires_candidate_payment=policy.requires_candidate_payment,
        compensation_summary=policy.compensation_summary,
        safety_notes=policy.safety_notes,
    )


@router.post("/scrape", response_model=JobScrapeResult)
async def scrape_jobs(
    payload: JobScrapeRequest,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    async with httpx.AsyncClient(timeout=30) as client:
        tasks: list[asyncio.Task[list[JobListing]]] = []
        for company in payload.greenhouse_companies:
            tasks.append(
                asyncio.create_task(
                    fetch_greenhouse_jobs(
                        company=company,
                        title_keywords=payload.title_keywords,
                        limit=payload.limit_per_company,
                        client=client,
                    )
                )
            )
        for company in payload.lever_companies:
            tasks.append(
                asyncio.create_task(
                    fetch_lever_jobs(
                        company=company,
                        title_keywords=payload.title_keywords,
                        limit=payload.limit_per_company,
                        client=client,
                    )
                )
            )

        results = await asyncio.gather(*tasks) if tasks else []

    jobs: list[JobListing] = []
    for batch in results:
        for job in batch:
            policy = analyze_job(
                title=job.job_title,
                description=job.description,
                employment_type=job.employment_type,
                application_url=str(job.application_url),
            )
            if not policy.is_internship:
                continue
            if not policy.is_legit or policy.requires_candidate_payment:
                continue

            job.is_paid = policy.is_paid
            job.is_legit = policy.is_legit
            job.requires_candidate_payment = policy.requires_candidate_payment
            job.compensation_summary = policy.compensation_summary
            job.safety_notes = policy.safety_notes
            job.is_internship = policy.is_internship
            jobs.append(job)

    inserted, updated = upsert_jobs(db, jobs)

    return JobScrapeResult(inserted=inserted, updated=updated, total_seen=len(jobs))


@router.get("", response_model=list[JobListing])
def list_jobs(
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
    source: str | None = None,
    paid_only: bool = False,
    skip: int = 0,
    limit: int = 50,
):
    query = db.query(ScrapedJob)
    if source:
        query = query.filter(ScrapedJob.source == source)

    jobs = query.order_by(ScrapedJob.scraped_at.desc()).offset(skip).limit(limit).all()

    listings: list[JobListing] = []
    for job in jobs:
        listing = _to_listing(job)
        if not listing.is_internship:
            continue
        if not listing.is_legit or listing.requires_candidate_payment:
            continue
        listings.append(listing)

    if paid_only:
        listings = [listing for listing in listings if listing.is_paid is True]

    listings.sort(key=lambda item: item.posted_date or "", reverse=True)
    listings.sort(key=lambda item: 0 if item.is_paid else 1)
    return listings
