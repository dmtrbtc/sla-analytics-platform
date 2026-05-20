"""Export pipeline Celery tasks — report generation, data export, signed exports."""
import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app, exponential_backoff
from app.core.database import sync_session_factory

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, soft_time_limit=600, time_limit=720)
def generate_export(self, export_id: str, export_type: str, params: dict) -> dict:
    """Generate an export (CSV, JSON, PDF) asynchronously."""
    from app.services.export_service import run_export

    db = sync_session_factory()
    try:
        result = run_export(db, export_id, export_type, params)
        logger.info("Export %s (%s) completed", export_id, export_type)
        return {"export_id": export_id, "status": "completed", "result": result}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, soft_time_limit=300, time_limit=360)
def sign_export(self, export_id: str) -> dict:
    """Sign an export with org-specific key."""
    from app.services.export_service import sign_export_file

    try:
        result = sign_export_file(export_id)
        return {"export_id": export_id, "signed": result}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise


@celery_app.task(bind=True, max_retries=2, soft_time_limit=120, time_limit=180)
def purge_old_exports(self, days: int = 30) -> dict:
    """Purge export files older than N days."""
    from app.services.export_service import purge_exports

    db = sync_session_factory()
    try:
        count = purge_exports(db, days)
        return {"purged": count}
    except Exception:
        try:
            self.retry(countdown=exponential_backoff(self))
        except Exception:
            raise
    finally:
        db.close()
