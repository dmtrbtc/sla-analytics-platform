"""Celery application configuration with dedicated queues, priorities,
dead letter handling, exponential backoff, and timeout protection."""

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
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    imports=[
        "app.tasks.import_tasks",
        "app.tasks.report_tasks",
        "app.tasks.maintenance_tasks",
    ],
    task_default_priority=5,
    task_queue_max_priority=10,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=300000,
    task_soft_time_limit=3600,
    task_time_limit=3900,
    task_routes={
        "app.tasks.import_tasks.*": {"queue": "imports"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
    },
    task_annotations={
        "app.tasks.import_tasks.run_import_pipeline": {
            "priority": 3,
            "soft_time_limit": 7200,
            "time_limit": 7800,
        },
        "app.tasks.import_tasks.compute_sla_step": {
            "priority": 2,
            "soft_time_limit": 3600,
            "time_limit": 3900,
        },
        "app.tasks.report_tasks.generate_report": {
            "priority": 4,
            "soft_time_limit": 1800,
            "time_limit": 2100,
        },
        "app.tasks.maintenance_tasks.*": {
            "priority": 8,
            "soft_time_limit": 7200,
            "time_limit": 7800,
        },
    },
)


def exponential_backoff(self) -> int:
    """Calculate exponential backoff delay.

    Formula: min(30 * 2^retries, 3600) with ±25% jitter.
    """
    import random

    retries = self.request.retries
    base_delay = 30 * (2**retries)
    delay = min(base_delay, 3600)
    jitter = random.uniform(0.75, 1.25)
    return int(delay * jitter)
