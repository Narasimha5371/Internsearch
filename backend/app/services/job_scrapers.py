from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import httpx

from app.schemas.job import JobListing
from app.services.job_policy import analyze_job


def _match_title(title: str, keywords: Iterable[str]) -> bool:
    lowered = title.lower()
    for keyword in keywords:
        if keyword.lower() in lowered:
            return True
    return False


def _safe_company_name(company_slug: str, payload: dict) -> str:
    company = payload.get("company")
    if isinstance(company, dict):
        return company.get("name") or company_slug
    if isinstance(company, str):
        return company
    return company_slug


async def fetch_greenhouse_jobs(
    company: str,
    title_keywords: list[str],
    limit: int,
    client: httpx.AsyncClient,
) -> list[JobListing]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
    response = await client.get(url)
    if response.status_code != 200:
        return []

    data = response.json()
    jobs = data.get("jobs", [])
    results: list[JobListing] = []

    for job in jobs:
        title = job.get("title") or ""
        if title_keywords and not _match_title(title, title_keywords):
            continue

        application_url = job.get("absolute_url")
        if not application_url:
            continue

        policy = analyze_job(
            title=title,
            description=job.get("content"),
            employment_type=None,
            application_url=application_url,
        )
        if not policy.is_internship:
            continue
        if not policy.is_legit or policy.requires_candidate_payment:
            continue

        results.append(
            JobListing(
                job_title=title,
                company=_safe_company_name(company, job),
                location=(job.get("location") or {}).get("name"),
                employment_type=None,
                required_skills=[],
                description=job.get("content"),
                application_url=application_url,
                source="greenhouse",
                source_job_id=str(job.get("id")) if job.get("id") else None,
                posted_date=job.get("updated_at"),
                is_internship=policy.is_internship,
                is_paid=policy.is_paid,
                is_legit=policy.is_legit,
                requires_candidate_payment=policy.requires_candidate_payment,
                compensation_summary=policy.compensation_summary,
                safety_notes=policy.safety_notes,
            )
        )

        if len(results) >= limit:
            break

    return results


async def fetch_lever_jobs(
    company: str,
    title_keywords: list[str],
    limit: int,
    client: httpx.AsyncClient,
) -> list[JobListing]:
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    response = await client.get(url)
    if response.status_code != 200:
        return []

    jobs = response.json()
    results: list[JobListing] = []

    for job in jobs:
        title = job.get("text") or ""
        if title_keywords and not _match_title(title, title_keywords):
            continue

        application_url = job.get("hostedUrl") or job.get("applyUrl")
        if not application_url:
            continue

        created_at = job.get("createdAt")
        posted_date: str | None = None
        if isinstance(created_at, (int, float)):
            posted_date = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).date().isoformat()

        categories = job.get("categories") or {}
        policy = analyze_job(
            title=title,
            description=job.get("description"),
            employment_type=categories.get("commitment"),
            application_url=application_url,
        )
        if not policy.is_internship:
            continue
        if not policy.is_legit or policy.requires_candidate_payment:
            continue

        results.append(
            JobListing(
                job_title=title,
                company=company,
                location=categories.get("location"),
                employment_type=categories.get("commitment"),
                required_skills=[],
                description=job.get("description"),
                application_url=application_url,
                source="lever",
                source_job_id=job.get("id"),
                posted_date=posted_date,
                is_internship=policy.is_internship,
                is_paid=policy.is_paid,
                is_legit=policy.is_legit,
                requires_candidate_payment=policy.requires_candidate_payment,
                compensation_summary=policy.compensation_summary,
                safety_notes=policy.safety_notes,
            )
        )

        if len(results) >= limit:
            break

    return results
