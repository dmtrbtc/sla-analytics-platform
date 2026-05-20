"""Analytics Celery tasks: materialized view refresh, stale detection, cache warm."""
import logging

from app.core.celery_app import celery_app, exponential_backoff
from app.core.database import sync_session_factory

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, soft_time_limit=300, time_limit=360)
def stale_view_check(self) -> dict:
    """Check if materialized views are stale and return status."""
    from app.services.analytics.materialized_view_service import check_view_staleness

    db = sync_session_factory()
    try:
        status = check_view_staleness(db)
        stale_count = sum(1 for s in status if s.get("is_stale"))
        logger.info("Stale view check: %d/%d views stale", stale_count, len(status))
        return {"total": len(status), "stale": stale_count, "views": status}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, soft_time_limit=300, time_limit=360)
def auto_refresh_extended_views(self) -> dict:
    """Create and refresh extended materialized views."""
    from app.services.analytics.materialized_view_service import ensure_extended_views, refresh_all_views

    db = sync_session_factory()
    try:
        created = ensure_extended_views(db)
        if created:
            logger.info("Created new extended views: %s", created)
        results = refresh_all_views(db, concurrently=True)
        return {"created": created, "refresh_results": results}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, soft_time_limit=120, time_limit=180)
def warm_analytics_cache(self) -> dict:
    """Warm analytics cache by hitting key endpoints."""
    import requests

    from app.core.config import settings

    base = "http://localhost:8000/api/v1"
    endpoints = [
        "/analytics/overview?days=30",
        "/analytics/overview?days=90",
        "/analytics/bottlenecks?days=90",
        "/analytics/sla-risks?limit=50",
        "/dashboards/executive",
        "/dashboards/queue-performance",
    ]
    results = {}
    for ep in endpoints:
        try:
            resp = requests.get(f"{base}{ep}", timeout=10)
            results[ep] = resp.status_code
        except Exception as exc:
            results[ep] = str(exc)
    logger.info("Cache warm: %s", results)
    return results
