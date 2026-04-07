from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, get_current_user
from app.db.deps import get_db
from app.db.models import AutopilotRunLog, AutopilotSettings
from app.schemas.autopilot import (
    AutopilotRunLogItem,
    AutopilotRunNowResponse,
    AutopilotSettingsRead,
    AutopilotSettingsUpdate,
)
from app.services.users import get_or_create_user
from app.workers.autopilot_tasks import run_autopilot_for_user_task

router = APIRouter(prefix="/autopilot", tags=["autopilot"])


def _to_settings_read(settings: AutopilotSettings) -> AutopilotSettingsRead:
    return AutopilotSettingsRead(
        id=settings.id,
        user_id=settings.user_id,
        enabled=settings.enabled,
        auto_submit=settings.auto_submit,
        paid_only=settings.paid_only,
        legit_only=settings.legit_only,
        max_applications_per_day=settings.max_applications_per_day,
        limit_per_company=settings.limit_per_company,
        greenhouse_companies=settings.greenhouse_companies or [],
        lever_companies=settings.lever_companies or [],
        title_keywords=settings.title_keywords or ["intern"],
        created_at=settings.created_at.isoformat(),
        updated_at=settings.updated_at.isoformat(),
    )


def _to_run_item(run: AutopilotRunLog) -> AutopilotRunLogItem:
    return AutopilotRunLogItem(
        id=run.id,
        user_id=run.user_id,
        trigger=run.trigger,
        status=run.status,
        jobs_seen=run.jobs_seen,
        jobs_qualified=run.jobs_qualified,
        applications_queued=run.applications_queued,
        message=run.message,
        details_json=run.details_json,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


def _get_or_create_settings(db: Session, user_id) -> AutopilotSettings:
    settings = db.query(AutopilotSettings).filter(AutopilotSettings.user_id == user_id).first()
    if settings:
        return settings

    settings = AutopilotSettings(
        user_id=user_id,
        enabled=False,
        auto_submit=False,
        paid_only=True,
        legit_only=True,
        max_applications_per_day=5,
        limit_per_company=25,
        greenhouse_companies=[],
        lever_companies=[],
        title_keywords=["intern"],
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/settings", response_model=AutopilotSettingsRead)
def get_autopilot_settings(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = get_or_create_user(db, current_user.user_id, current_user.email)
    settings = _get_or_create_settings(db, user.id)
    return _to_settings_read(settings)


@router.put("/settings", response_model=AutopilotSettingsRead)
def update_autopilot_settings(
    payload: AutopilotSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = get_or_create_user(db, current_user.user_id, current_user.email)
    settings = _get_or_create_settings(db, user.id)

    settings.enabled = payload.enabled
    settings.auto_submit = payload.auto_submit
    settings.paid_only = payload.paid_only
    settings.legit_only = payload.legit_only
    settings.max_applications_per_day = payload.max_applications_per_day
    settings.limit_per_company = payload.limit_per_company
    settings.greenhouse_companies = payload.greenhouse_companies
    settings.lever_companies = payload.lever_companies
    settings.title_keywords = payload.title_keywords

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return _to_settings_read(settings)


@router.post("/run-now", response_model=AutopilotRunNowResponse)
def run_autopilot_now(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = get_or_create_user(db, current_user.user_id, current_user.email)
    _get_or_create_settings(db, user.id)

    task = run_autopilot_for_user_task.delay(str(user.id), "manual")
    return AutopilotRunNowResponse(task_id=task.id, status="queued")


@router.get("/runs", response_model=list[AutopilotRunLogItem])
def list_autopilot_runs(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    limit: int = 20,
):
    user = get_or_create_user(db, current_user.user_id, current_user.email)
    rows = (
        db.query(AutopilotRunLog)
        .filter(AutopilotRunLog.user_id == user.id)
        .order_by(AutopilotRunLog.started_at.desc())
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return [_to_run_item(item) for item in rows]
