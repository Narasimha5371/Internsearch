from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import uuid

import httpx

from app.db.models import (
    ApplicationLog,
    AutopilotRunLog,
    AutopilotSettings,
    ParsedResume,
    ScrapedJob,
)
from app.db.session import SessionLocal
from app.schemas.candidate import CandidateProfile
from app.schemas.job import JobListing
from app.services.job_policy import analyze_job
from app.services.job_scrapers import fetch_greenhouse_jobs, fetch_lever_jobs
from app.services.job_store import upsert_jobs
from app.workers.application_tasks import run_application_task
from app.workers.celery_app import celery_app


def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _find_job_record(db, listing: JobListing) -> ScrapedJob | None:
    if listing.source_job_id:
        row = (
            db.query(ScrapedJob)
            .filter(
                ScrapedJob.source == listing.source,
                ScrapedJob.source_job_id == listing.source_job_id,
            )
            .first()
        )
        if row:
            return row

    return db.query(ScrapedJob).filter(ScrapedJob.application_url == str(listing.application_url)).first()


async def _scrape_jobs_for_settings(settings: AutopilotSettings) -> list[JobListing]:
    async with httpx.AsyncClient(timeout=30) as client:
        tasks: list[asyncio.Task[list[JobListing]]] = []
        for company in settings.greenhouse_companies or []:
            tasks.append(
                asyncio.create_task(
                    fetch_greenhouse_jobs(
                        company=company,
                        title_keywords=settings.title_keywords or ["intern"],
                        limit=settings.limit_per_company,
                        client=client,
                    )
                )
            )

        for company in settings.lever_companies or []:
            tasks.append(
                asyncio.create_task(
                    fetch_lever_jobs(
                        company=company,
                        title_keywords=settings.title_keywords or ["intern"],
                        limit=settings.limit_per_company,
                        client=client,
                    )
                )
            )

        results = await asyncio.gather(*tasks) if tasks else []

    return [item for batch in results for item in batch]


@celery_app.task(bind=True, name="app.workers.autopilot.run_for_user")
def run_autopilot_for_user_task(self, user_id: str, trigger: str = "scheduled") -> dict:
    db = SessionLocal()
    run_log = None

    try:
        user_uuid = uuid.UUID(user_id)
        run_log = AutopilotRunLog(
            user_id=user_uuid,
            trigger=trigger,
            status="running",
            jobs_seen=0,
            jobs_qualified=0,
            applications_queued=0,
            message=None,
            details_json=None,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
        )
        db.add(run_log)
        db.commit()
        db.refresh(run_log)

        settings = db.query(AutopilotSettings).filter(AutopilotSettings.user_id == user_uuid).first()
        if not settings:
            run_log.status = "skipped"
            run_log.message = "Autopilot settings not found."
            run_log.completed_at = datetime.now(timezone.utc)
            db.add(run_log)
            db.commit()
            return {"status": "skipped", "reason": "settings_not_found"}

        if trigger == "scheduled" and not settings.enabled:
            run_log.status = "skipped"
            run_log.message = "Autopilot disabled."
            run_log.completed_at = datetime.now(timezone.utc)
            db.add(run_log)
            db.commit()
            return {"status": "skipped", "reason": "autopilot_disabled"}

        jobs = asyncio.run(_scrape_jobs_for_settings(settings))
        run_log.jobs_seen = len(jobs)

        if jobs:
            upsert_jobs(db, jobs)

        latest_resume = (
            db.query(ParsedResume)
            .filter(ParsedResume.user_id == user_uuid)
            .order_by(ParsedResume.created_at.desc())
            .first()
        )
        if not latest_resume or not latest_resume.parsed_json:
            run_log.status = "failed"
            run_log.message = "No parsed resume found for user."
            run_log.completed_at = datetime.now(timezone.utc)
            db.add(run_log)
            db.commit()
            return {"status": "failed", "reason": "missing_resume"}

        candidate = CandidateProfile.model_validate(latest_resume.parsed_json)
        todays_count = (
            db.query(ApplicationLog)
            .filter(
                ApplicationLog.user_id == user_uuid,
                ApplicationLog.created_at >= _today_start_utc(),
            )
            .count()
        )
        remaining_budget = max(0, settings.max_applications_per_day - todays_count)
        if remaining_budget == 0:
            run_log.status = "completed"
            run_log.message = "Daily application cap reached."
            run_log.completed_at = datetime.now(timezone.utc)
            db.add(run_log)
            db.commit()
            return {"status": "completed", "queued": 0, "reason": "daily_cap_reached"}

        existing_job_ids = {
            row[0]
            for row in db.query(ApplicationLog.job_id)
            .filter(ApplicationLog.user_id == user_uuid, ApplicationLog.job_id.is_not(None))
            .all()
        }

        qualified: list[tuple[JobListing, ScrapedJob, bool]] = []
        for listing in jobs:
            policy = analyze_job(
                title=listing.job_title,
                description=listing.description,
                employment_type=listing.employment_type,
                application_url=str(listing.application_url),
            )

            if not policy.is_internship:
                continue
            if settings.legit_only and not policy.is_legit:
                continue
            if settings.paid_only and policy.is_paid is not True:
                continue

            row = _find_job_record(db, listing)
            if not row:
                continue
            if row.id in existing_job_ids:
                continue

            should_auto_submit = bool(settings.auto_submit and policy.is_paid is True)
            qualified.append((listing, row, should_auto_submit))

        qualified.sort(key=lambda entry: 0 if entry[0].is_paid else 1)
        run_log.jobs_qualified = len(qualified)

        queued_count = 0
        for listing, row, should_auto_submit in qualified:
            if queued_count >= remaining_budget:
                break

            log = ApplicationLog(
                user_id=user_uuid,
                job_id=row.id,
                status="queued",
                mode="auto" if should_auto_submit else "dry_run",
                result_json={
                    "application_url": row.application_url,
                    "autopilot": True,
                    "autopilot_run_id": str(run_log.id),
                },
                error_message=None,
            )
            db.add(log)
            db.commit()
            db.refresh(log)

            run_application_task.delay(
                log_id=str(log.id),
                application_url=row.application_url,
                candidate_json=candidate.model_dump(),
                resume_file_path=latest_resume.file_path,
                auto_submit=should_auto_submit,
            )
            queued_count += 1

        run_log.status = "completed"
        run_log.applications_queued = queued_count
        run_log.message = "Autopilot cycle finished."
        run_log.details_json = {
            "remaining_budget": remaining_budget,
            "trigger": trigger,
        }
        run_log.completed_at = datetime.now(timezone.utc)
        db.add(run_log)
        db.commit()

        return {
            "status": "completed",
            "jobs_seen": run_log.jobs_seen,
            "jobs_qualified": run_log.jobs_qualified,
            "applications_queued": queued_count,
        }
    except Exception as exc:  # noqa: BLE001
        if run_log:
            run_log.status = "failed"
            run_log.message = str(exc)
            run_log.completed_at = datetime.now(timezone.utc)
            db.add(run_log)
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="app.workers.autopilot.run_cycle")
def run_autopilot_cycle_task(self) -> dict:
    db = SessionLocal()
    try:
        enabled_settings = db.query(AutopilotSettings).filter(AutopilotSettings.enabled.is_(True)).all()
        task_ids: list[str] = []
        for settings in enabled_settings:
            task = run_autopilot_for_user_task.delay(str(settings.user_id), "scheduled")
            task_ids.append(task.id)

        return {
            "status": "queued",
            "users": len(enabled_settings),
            "task_ids": task_ids,
        }
    finally:
        db.close()
