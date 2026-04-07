import asyncio
import uuid
from pathlib import Path

from app.core.config import settings
from app.db.models import ApplicationLog
from app.db.session import SessionLocal
from app.schemas.candidate import CandidateProfile
from app.services.automation import run_application
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, name="app.workers.run_application")
def run_application_task(
    self,
    log_id: str,
    application_url: str,
    candidate_json: dict,
    resume_file_path: str | None,
    auto_submit: bool,
) -> dict:
    db = SessionLocal()
    log = None
    try:
        log_uuid = uuid.UUID(log_id)
        log = db.query(ApplicationLog).filter(ApplicationLog.id == log_uuid).first()
        if log:
            log.status = "running"
            db.add(log)
            db.commit()

        candidate = CandidateProfile.model_validate(candidate_json)
        artifacts_dir = Path(settings.artifacts_dir) / "applications" / log_id
        result = asyncio.run(
            run_application(
                application_url=application_url,
                candidate=candidate,
                resume_file_path=resume_file_path,
                auto_submit=auto_submit,
                artifacts_dir=artifacts_dir,
            )
        )

        if log:
            log.status = result.get("status", "completed")
            log.result_json = result
            db.add(log)
            db.commit()

        return result
    except Exception as exc:  # noqa: BLE001
        if log:
            if self.request.retries >= self.max_retries:
                log.status = "failed"
            else:
                log.status = "retrying"
            log.error_message = str(exc)
            db.add(log)
            db.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (self.request.retries + 1))
        raise
    finally:
        db.close()
