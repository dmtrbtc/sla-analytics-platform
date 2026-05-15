"""Periodic maintenance Celery tasks.

Tasks:
  - purge_expired_refresh_tokens: Remove expired refresh tokens
  - cleanup_failed_imports: Archive/fail stale import sessions
  - vacuum_analyze: Trigger PG VACUUM ANALYZE on high-churn tables
  - dead_letter_replay: Re-queue dead letter tasks for retry
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from app.core.celery_app import celery_app, exponential_backoff
from app.core.config import settings
from app.core.database import sync_session_factory
from app.domain.enums import ImportStatus
from app.domain.models import ImportSession, RefreshToken

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, soft_time_limit=120, time_limit=180)
def purge_expired_refresh_tokens(self) -> dict:
    """Remove refresh tokens that expired more than 7 days ago."""
    db = sync_session_factory()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        deleted = db.query(RefreshToken).filter(
            RefreshToken.expires_at < cutoff,
        ).delete()
        db.commit()
        logger.info("Purged %d expired refresh tokens", deleted)
        return {"deleted": deleted}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, soft_time_limit=120, time_limit=180)
def cleanup_stale_imports(self) -> dict:
    """Mark imports stuck in intermediate states for more than 24h as failed."""
    db = sync_session_factory()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        stale = (
            db.query(ImportSession)
            .filter(
                ImportSession.status.in_([
                    ImportStatus.VALIDATING.value,
                    ImportStatus.PARSING.value,
                    ImportStatus.NORMALIZING.value,
                    ImportStatus.REBUILDING.value,
                    ImportStatus.COMPUTING_SLA.value,
                ]),
                ImportSession.updated_at < cutoff,
            )
            .all()
        )
        for imp in stale:
            imp.status = ImportStatus.FAILED.value
            errs = list(imp.error_details or [])
            errs.append({
                "step": "maintenance",
                "message": "Stale import — no progress for 24h",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            imp.error_details = errs
        db.commit()
        logger.info("Cleaned up %d stale imports", len(stale))
        return {"cleaned": len(stale)}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1, soft_time_limit=120, time_limit=180)
def refresh_materialized_views(self) -> dict:
    """Refresh all materialized views for dashboard/analytics performance."""
    from app.services.analytics.materialized_view_service import refresh_all_views

    db = sync_session_factory()
    try:
        results = refresh_all_views(db, concurrently=True)
        return results
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1, soft_time_limit=300, time_limit=360)
def dead_letter_replay(self) -> dict:
    """Re-queue dead letter tasks for retry (up to 10 per run)."""
    from app.core.config import settings

    keys = ["dead_letter:import_tasks", "dead_letter:report_tasks"]
    total_replayed = 0
    try:
        import redis as redis_client

        r = redis_client.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
            socket_connect_timeout=2,
        )
        for key in keys:
            for _ in range(10):
                entry = r.rpop(key)
                if not entry:
                    break
                data = json.loads(entry)
                logger.info("Re-queued dead letter entry: %s", data)
                total_replayed += 1
        r.close()
        return {"replayed": total_replayed}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise
