"""Celery application configuration with dedicated queues, priorities,
dead letter handling, exponential backoff, and timeout protection."""

from celery import Celery

from app.core.config import settings
from app.core.celery_monitoring import MonitoredTask

celery_app = Celery(
    "sla_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    task_cls=MonitoredTask,
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
        "app.tasks.analytics_tasks",
        "app.tasks.export_tasks",
        "app.tasks.notification_tasks",
        "app.services.sla.compute_orchestrator",
        "app.services.operations.self_healing",
    ],
    task_default_priority=5,
    task_queue_max_priority=10,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=300000,
    task_soft_time_limit=3600,
    task_time_limit=3900,
    beat_schedule={
        "refresh-materialized-views-every-5min": {
            "task": "app.tasks.maintenance_tasks.refresh_materialized_views",
            "schedule": 300.0,
        },
        "stale-view-check-every-1h": {
            "task": "app.tasks.analytics_tasks.stale_view_check",
            "schedule": 3600.0,
        },
        "auto-refresh-extended-views-every-15min": {
            "task": "app.tasks.analytics_tasks.auto_refresh_extended_views",
            "schedule": 900.0,
        },
        "auto-heal-check-every-5min": {
            "task": "app.services.operations.self_healing.auto_heal_check",
            "schedule": 300.0,
        },
        "analytics-cache-warm-every-30min": {
            "task": "app.tasks.analytics_tasks.warm_analytics_cache",
            "schedule": 1800.0,
        },
        "purge-old-exports-daily": {
            "task": "app.tasks.export_tasks.purge_old_exports",
            "schedule": 86400.0,
        },
    },
    task_routes={
        "app.tasks.import_tasks.*": {"queue": "imports"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
        "app.tasks.analytics_tasks.*": {"queue": "analytics"},
        "app.tasks.export_tasks.*": {"queue": "exports"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.services.sla.compute_orchestrator.*": {"queue": "sla_compute"},
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
