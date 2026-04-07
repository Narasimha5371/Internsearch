from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "job_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.application_tasks",
        "app.workers.autopilot_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "autopilot-cycle": {
            "task": "app.workers.autopilot.run_cycle",
            "schedule": max(settings.autopilot_cycle_minutes, 5) * 60,
        }
    },
)
