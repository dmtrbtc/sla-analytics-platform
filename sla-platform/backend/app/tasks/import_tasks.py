"""Import pipeline Celery tasks with exponential backoff, timeouts, and dead letter routing."""

import logging
from datetime import datetime, timezone

from celery import chain

from app.core.celery_app import celery_app, exponential_backoff
from app.core.database import sync_session_factory
from app.core.websocket_manager import publish_ws_event
from app.domain.enums import ImportStatus
from app.domain.models import ImportSession

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


@celery_app.task(
    bind=True, max_retries=2, default_retry_delay=30,
    soft_time_limit=120, time_limit=150,
)
def run_import_pipeline(self, import_id: str) -> dict:
    logger.info("Starting import pipeline chain", extra={"import_id": import_id})
    workflow = chain(
        validate_step.s(import_id),
        backlog_step.s(),
        parse_step.s(),
        normalize_step.s(),
        rebuild_step.s(),
        compute_sla_step.s(),
        complete_step.s(),
    )
    result = workflow.apply_async()
    return {"import_id": import_id, "chain_id": result.id}


@celery_app.task(bind=True, max_retries=MAX_RETRIES, soft_time_limit=300, time_limit=360)
def validate_step(self, import_id: str) -> dict:
    logger.info("Validate step", extra={"import_id": import_id})
    db = sync_session_factory()
    try:
        imp = db.query(ImportSession).filter_by(id=import_id).first()
        if not imp:
            raise ValueError(f"ImportSession {import_id} not found")
        if not imp.backlog_file:
            raise ValueError("Backlog file is required")
        if not imp.history_file:
            raise ValueError("History file is required")
        imp.status = ImportStatus.VALIDATING.value
        db.commit()
        return {"import_id": import_id, "validated": True}
    except Exception:
        _record_error(db, import_id, "validate")
        _retry_or_fail(self, db, import_id, "validate")
    else:
        _publish("import_progress", import_id=import_id, step="validate", status="completed", progress=10)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=MAX_RETRIES, soft_time_limit=600, time_limit=720)
def backlog_step(self, prev_result: dict) -> dict:
    import_id = prev_result["import_id"]
    logger.info("Backlog step", extra={"import_id": import_id})
    from app.services.backlog_service import BacklogService
    db = sync_session_factory()
    try:
        _set_status(db, import_id, ImportStatus.VALIDATING.value)
        stats = BacklogService.load_backlog(db, import_id)
        _update_stats(db, import_id, stats)
        logger.info("Backlog load complete", extra={"import_id": import_id, **stats})
        return {"import_id": import_id, "backlog_stats": stats}
    except Exception:
        _record_error(db, import_id, "backlog")
        _retry_or_fail(self, db, import_id, "backlog")
    else:
        _publish("import_progress", import_id=import_id, step="backlog", status="completed", progress=25)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=MAX_RETRIES, soft_time_limit=600, time_limit=720)
def parse_step(self, prev_result: dict) -> dict:
    import_id = prev_result["import_id"]
    logger.info("Parse step", extra={"import_id": import_id})
    from app.services.parser_service import ParserService
    db = sync_session_factory()
    try:
        _set_status(db, import_id, ImportStatus.PARSING.value)
        stats = ParserService.parse_and_load(db, import_id)
        _update_stats(db, import_id, stats)
        if stats.get("errors"):
            raise ValueError(f"Parse errors: {stats['errors']}")
        logger.info("Parse complete", extra={"import_id": import_id, **stats})
        return {"import_id": import_id, "parse_stats": stats}
    except Exception:
        _record_error(db, import_id, "parse")
        _retry_or_fail(self, db, import_id, "parse")
    else:
        _publish("import_progress", import_id=import_id, step="parse", status="completed", progress=40)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=MAX_RETRIES, soft_time_limit=600, time_limit=720)
def normalize_step(self, prev_result: dict) -> dict:
    import_id = prev_result["import_id"]
    logger.info("Normalize step", extra={"import_id": import_id})
    from app.services.normalizer_service import NormalizerService
    db = sync_session_factory()
    try:
        _set_status(db, import_id, ImportStatus.NORMALIZING.value)
        stats = NormalizerService.normalize(db, import_id)
        _update_stats(db, import_id, stats)
        logger.info("Normalize complete", extra={"import_id": import_id, **stats})
        return {"import_id": import_id, "normalize_stats": stats}
    except Exception:
        _record_error(db, import_id, "normalize")
        _retry_or_fail(self, db, import_id, "normalize")
    else:
        _publish("import_progress", import_id=import_id, step="normalize", status="completed", progress=55)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=MAX_RETRIES, soft_time_limit=600, time_limit=720)
def rebuild_step(self, prev_result: dict) -> dict:
    import_id = prev_result["import_id"]
    logger.info("Rebuild step", extra={"import_id": import_id})
    from app.services.reconstructor_service import ReconstructorService
    db = sync_session_factory()
    try:
        _set_status(db, import_id, ImportStatus.REBUILDING.value)
        stats = ReconstructorService.rebuild(db, import_id)
        _update_stats(db, import_id, stats)
        logger.info("Rebuild complete", extra={"import_id": import_id, **stats})
        return {"import_id": import_id, "rebuild_stats": stats}
    except Exception:
        _record_error(db, import_id, "rebuild")
        _retry_or_fail(self, db, import_id, "rebuild")
    else:
        _publish("import_progress", import_id=import_id, step="rebuild", status="completed", progress=70)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=MAX_RETRIES, soft_time_limit=1200, time_limit=1500)
def compute_sla_step(self, prev_result: dict) -> dict:
    import_id = prev_result["import_id"]
    logger.info("SLA computation step", extra={"import_id": import_id})
    from app.services.sla_engine import SLAEngine
    db = sync_session_factory()
    try:
        _set_status(db, import_id, ImportStatus.COMPUTING_SLA.value)
        stats = SLAEngine.compute_for_import(db, import_id)
        _update_stats(db, import_id, stats)
        logger.info("SLA computation complete", extra={"import_id": import_id, **stats})
        return {"import_id": import_id, "sla_stats": stats}
    except Exception:
        _record_error(db, import_id, "compute_sla")
        _retry_or_fail(self, db, import_id, "compute_sla")
    else:
        _publish("import_progress", import_id=import_id, step="compute_sla", status="completed", progress=85)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=MAX_RETRIES, soft_time_limit=30, time_limit=60)
def complete_step(self, prev_result: dict) -> dict:
    import_id = prev_result["import_id"]
    logger.info("Complete step", extra={"import_id": import_id})
    db = sync_session_factory()
    try:
        imp = db.query(ImportSession).filter_by(id=import_id).first()
        if imp:
            imp.status = ImportStatus.COMPLETED.value
            imp.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("Import completed", extra={"import_id": import_id})
        return {"import_id": import_id, "status": "completed"}
    except Exception:
        _record_error(db, import_id, "complete")
        _retry_or_fail(self, db, import_id, "complete")
    else:
        _publish("import_progress", import_id=import_id, step="complete", status="completed", progress=100)
    finally:
        db.close()


def _publish(event_type: str, **kwargs) -> None:
    """Publish a WebSocket event via Redis pub/sub."""
    publish_ws_event({"type": event_type, "ts": datetime.now(timezone.utc).timestamp(), **kwargs})


def _set_status(db, import_id: str, status: str) -> None:
    db.query(ImportSession).filter_by(id=import_id).update({"status": status})
    db.commit()


def _update_stats(db, import_id: str, stats: dict) -> None:
    imp = db.query(ImportSession).filter_by(id=import_id).first()
    if imp:
        current = dict(imp.stats or {})
        current.update(stats)
        imp.stats = current
        db.commit()


def _record_error(db, import_id: str, step: str) -> None:
    try:
        db.rollback()
    except Exception:
        pass
    imp = db.query(ImportSession).filter_by(id=import_id).first()
    if imp:
        errs = list(imp.error_details or [])
        errs.append({
            "step": step,
            "message": f"Task failed (retry {db.info.get('retry_count', 0)})",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        imp.error_details = errs
        db.commit()


def _retry_or_fail(self, db, import_id: str, step: str) -> None:
    """Retry with exponential backoff or fail permanently."""
    try:
        db.close()
    except Exception:
        pass
    try:
        self.retry(countdown=exponential_backoff(self))
    except self.MaxRetriesExceededError:
        _fail(import_id, step)
        raise


def _fail(import_id: str, step: str) -> None:
    """Mark import as failed and route to dead letter queue."""
    fresh = sync_session_factory()
    try:
        imp = fresh.query(ImportSession).filter_by(id=import_id).first()
        if imp:
            imp.status = ImportStatus.FAILED.value
            fresh.commit()
    finally:
        fresh.close()
    _route_to_dead_letter(import_id, step)
    _publish("import_progress", import_id=import_id, step=step, status="failed")
    logger.error("Import %s failed permanently at step %s", import_id, step)


def _route_to_dead_letter(import_id: str, step: str) -> None:
    """Push failed task info to Redis dead letter list."""
    from app.core.config import settings
    import json
    try:
        import redis as redis_client
        r = redis_client.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_connect_timeout=2,
        )
        entry = {
            "import_id": import_id,
            "step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r.lpush("dead_letter:import_tasks", json.dumps(entry))
        r.ltrim("dead_letter:import_tasks", 0, 999)
        r.expire("dead_letter:import_tasks", 86400 * 7)
        r.close()
    except Exception as e:
        logger.warning("Dead letter routing failed: %s", e)
