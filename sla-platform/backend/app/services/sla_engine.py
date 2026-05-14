"""SLA Engine orchestrator — coordinates rule matching, pause handling, and metric computation.

Entry point for the Celery pipeline. Delegates to sub-modules:
- rule_engine: match SLA definition to ticket
- pause_engine: compute pause intervals
- metrics_engine: compute all metric types
- business_hours: filter by schedule
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.models import SLADefinition, TicketSnapshot
from app.services.sla.rule_engine import match_sla
from app.services.sla.metrics_engine import MetricsEngine

logger = logging.getLogger(__name__)


class SLAEngine:

    @staticmethod
    def compute_for_import(db: Session, import_id: str) -> dict:
        """Compute SLA metrics for every ticket in *import_id*.

        Idempotent: deletes existing SLAMetric rows for this import before writing.
        """
        db.execute(
            text("DELETE FROM sla_metrics WHERE import_id = :import_id"),
            {"import_id": import_id},
        )
        db.commit()

        tickets = (
            db.query(TicketSnapshot)
            .filter(TicketSnapshot.last_import_id == import_id)
            .all()
        )
        sla_defs = (
            db.query(SLADefinition)
            .filter(SLADefinition.is_active == True)
            .all()
        )

        if not sla_defs:
            logger.warning("No active SLA definitions found — using defaults")
            sla_defs = [SLAEngine._default_sla_definition()]

        metrics_written = 0
        errors: list[dict] = []

        for ticket in tickets:
            try:
                sla_def = match_sla(ticket, sla_defs)
                if not sla_def:
                    continue
                metrics = MetricsEngine.compute_all(db, ticket, sla_def, import_id)
                if metrics:
                    for m in metrics:
                        db.add(m)
                    metrics_written += len(metrics)
            except Exception as exc:
                logger.exception("SLA computation failed for ticket %s", ticket.ticket_id)
                errors.append({"ticket_id": ticket.ticket_id, "error": str(exc)})

        if metrics_written > 0:
            db.commit()

        return {"metrics_written": metrics_written, "errors": errors}

    @staticmethod
    def _default_sla_definition() -> SLADefinition:
        return SLADefinition(
            id=0,
            name="Default Fallback",
            queue_pattern="*",
            priority=None,
            response_target_seconds=28800,
            resolution_target_seconds=144000,
            pause_on_pending=True,
            business_hours_only=False,
            business_hours=None,
            is_active=True,
        )
