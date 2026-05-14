"""Report generation Celery tasks."""

import json
import logging
import os
from datetime import datetime
from uuid import uuid4

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import sync_session_factory
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

EXPORT_DIR = os.path.join(settings.DATA_DIR, "exports")
_REPORT_STATUSES: dict = {}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=30)
def generate_report(self, report_type: str, fmt: str = "xlsx", params: dict | None = None) -> dict:
    report_id = str(uuid4())
    _REPORT_STATUSES[report_id] = {"status": "generating", "progress": 0}

    params = params or {}
    db = sync_session_factory()
    try:
        logger.info("Generating report", extra={"report_id": report_id, "type": report_type, "fmt": fmt})

        if report_type == "sla_breaches":
            result = ReportService.sla_breaches_report(
                db, import_id=params.get("import_id"), fmt=fmt
            )
        elif report_type == "team_performance":
            result = ReportService.team_performance_report(
                db, team_prefix=params.get("team_prefix"), fmt=fmt
            )
        elif report_type == "ticket_lifecycle":
            result = ReportService.ticket_lifecycle_report(db, fmt=fmt)
        elif report_type == "imports_summary":
            result = ReportService.imports_summary_report(db, fmt=fmt)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        _REPORT_STATUSES[report_id] = {
            "status": "completed",
            "progress": 100,
            "filename": result["filename"],
            "filepath": result["filepath"],
            "rows": result["rows"],
            "format": result["format"],
        }
        logger.info("Report generated", extra={"report_id": report_id, **result})
        return {"report_id": report_id, **result}

    except Exception as exc:
        logger.exception("Report generation failed")
        _REPORT_STATUSES[report_id] = {"status": "failed", "progress": 0, "error": str(exc)}
        raise
    finally:
        db.close()


def get_report_status(report_id: str) -> dict | None:
    return _REPORT_STATUSES.get(report_id)
