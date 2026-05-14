from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "sla_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    imports=["app.tasks.import_tasks", "app.tasks.report_tasks"],
    task_routes={
        "app.tasks.import_tasks.*": {"queue": "import"},
        "app.tasks.report_tasks.*": {"queue": "report"},
    },
)
