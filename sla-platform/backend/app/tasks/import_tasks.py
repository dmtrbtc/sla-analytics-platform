import logging
from datetime import datetime, timezone

from celery import chain

from app.core.celery_app import celery_app
from app.core.database import sync_session_factory
from app.domain.enums import ImportStatus
from app.domain.models import ImportSession

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
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


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
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
    except Exception as exc:
        _fail(db, import_id, str(exc), "validate")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
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
    except Exception as exc:
        logger.exception("Backlog step failed")
        _fail(db, import_id, str(exc), "backlog")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
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
    except Exception as exc:
        logger.exception("Parse failed")
        _fail(db, import_id, str(exc), "parse")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
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
    except Exception as exc:
        logger.exception("Normalize failed")
        _fail(db, import_id, str(exc), "normalize")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
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
    except Exception as exc:
        logger.exception("Rebuild failed")
        _fail(db, import_id, str(exc), "rebuild")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
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
    except Exception as exc:
        logger.exception("SLA computation failed")
        _fail(db, import_id, str(exc), "compute_sla")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1)
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
    except Exception as exc:
        logger.exception("Complete step failed")
        _fail(db, import_id, str(exc), "complete")
        raise
    finally:
        db.close()


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


def _fail(db, import_id: str, error: str, step: str) -> None:
    try:
        db.rollback()
    except Exception:
        pass
    fresh = sync_session_factory()
    try:
        imp = fresh.query(ImportSession).filter_by(id=import_id).first()
        if imp:
            errs = list(imp.error_details or [])
            errs.append({
                "step": step,
                "message": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            imp.error_details = errs
            imp.status = ImportStatus.FAILED.value
            fresh.commit()
    finally:
        fresh.close()
