from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, get_current_user
from app.db.deps import get_db
from app.db.models import ApplicationLog, ParsedResume, ScrapedJob
from app.schemas.application import ApplicationEnqueueResponse, ApplicationLogItem, ApplicationRequest
from app.schemas.candidate import CandidateProfile
from app.services.job_policy import analyze_job
from app.services.users import get_or_create_user
from app.workers.application_tasks import run_application_task

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/submit", response_model=ApplicationEnqueueResponse)
def submit_application(
    payload: ApplicationRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = get_or_create_user(db, current_user.user_id, current_user.email)
    job_id = payload.job_id

    if not job_id:
        raise HTTPException(
            status_code=400,
            detail="Manual application URLs are disabled for safety. Use a vetted job listing.",
        )

    job = db.query(ScrapedJob).filter(ScrapedJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    policy = analyze_job(
        title=job.job_title,
        description=job.description,
        employment_type=job.employment_type,
        application_url=job.application_url,
    )

    if not policy.is_internship:
        raise HTTPException(status_code=422, detail="Only internship roles can be submitted.")
    if not policy.is_legit:
        raise HTTPException(status_code=422, detail="This listing failed legitimacy checks.")
    if policy.requires_candidate_payment:
        raise HTTPException(
            status_code=422,
            detail="This listing appears to require candidate payment and is blocked.",
        )
    if payload.auto_submit and policy.is_paid is not True:
        raise HTTPException(
            status_code=422,
            detail="Auto-submit is limited to paid internships.",
        )

    application_url = job.application_url

    resume = (
        db.query(ParsedResume)
        .filter(ParsedResume.user_id == user.id)
        .order_by(ParsedResume.created_at.desc())
        .first()
    )
    if not resume or not resume.parsed_json:
        raise HTTPException(status_code=404, detail="No parsed resume found.")

    candidate = CandidateProfile.model_validate(resume.parsed_json)
    resume_path = payload.resume_file_path or resume.file_path

    log = ApplicationLog(
        user_id=user.id,
        job_id=job_id,
        status="queued",
        mode="auto" if payload.auto_submit else "dry_run",
        result_json={
            "application_url": application_url,
            "is_paid": policy.is_paid,
            "compensation_summary": policy.compensation_summary,
        },
        error_message=None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    async_result = run_application_task.delay(
        log_id=str(log.id),
        application_url=application_url,
        candidate_json=candidate.model_dump(),
        resume_file_path=resume_path,
        auto_submit=payload.auto_submit,
    )

    return ApplicationEnqueueResponse(log_id=log.id, task_id=async_result.id, status=log.status)


@router.get("", response_model=list[ApplicationLogItem])
def list_applications(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50,
):
    user = get_or_create_user(db, current_user.user_id, current_user.email)

    logs = (
        db.query(ApplicationLog)
        .filter(ApplicationLog.user_id == user.id)
        .order_by(ApplicationLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        ApplicationLogItem(
            id=log.id,
            status=log.status,
            mode=log.mode,
            application_url=(
                log.result_json.get("application_url")
                if log.result_json
                else log.job.application_url if log.job_id and log.job else None
            ),
            job_id=log.job_id,
            error_message=log.error_message,
            created_at=log.created_at.isoformat(),
            result_json=log.result_json,
        )
        for log in logs
    ]


@router.get("/{log_id}", response_model=ApplicationLogItem)
def get_application_log(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = get_or_create_user(db, current_user.user_id, current_user.email)
    log = (
        db.query(ApplicationLog)
        .filter(ApplicationLog.id == log_id, ApplicationLog.user_id == user.id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Application log not found.")

    return ApplicationLogItem(
        id=log.id,
        status=log.status,
        mode=log.mode,
        application_url=(
            log.result_json.get("application_url")
            if log.result_json
            else log.job.application_url if log.job_id and log.job else None
        ),
        job_id=log.job_id,
        error_message=log.error_message,
        created_at=log.created_at.isoformat(),
        result_json=log.result_json,
    )
