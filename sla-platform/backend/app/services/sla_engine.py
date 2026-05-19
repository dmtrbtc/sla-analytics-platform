"""SLA Engine orchestrator V2 — coordinates V2 rule matching, pause handling, timeline, and metrics.

Entry point for Celery pipeline. Uses:
- timeline_engine: reconstruct ticket lifecycle
- rule_engine: match SLA definitions with conditions
- pause_engine: compute pause intervals with audit
- metrics_engine: compute all metric types with risk
- business_hours: calendar-aware business time
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.models import SLADefinition, TicketSnapshot
from app.services.sla.rule_engine import match_sla
from app.services.sla.metrics_engine import MetricsEngine
from app.services.sla.timeline_engine import build_timeline, explain_ticket_timeline

logger = logging.getLogger(__name__)


class SLAEngine:

    @staticmethod
    def compute_for_import(db: Session, import_id: str) -> dict:
        """Compute SLA metrics for every ticket in *import_id*.

        Idempotent: deletes existing SLAMetric rows for this import before writing.
        Uses V2 engines with full timeline, pause audit, risk scoring, and efficiency metrics.
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
    def compute_for_ticket(
        db: Session,
        ticket: TicketSnapshot,
        import_id: str,
    ) -> dict:
        """Compute SLA metrics for a single ticket. Returns summary."""
        sla_defs = (
            db.query(SLADefinition)
            .filter(SLADefinition.is_active == True)
            .all()
        )
        if not sla_defs:
            sla_defs = [SLAEngine._default_sla_definition()]

        sla_def = match_sla(ticket, sla_defs)
        if not sla_def:
            return {"metrics_written": 0, "errors": [{"ticket_id": ticket.ticket_id, "error": "no SLA definition matched"}]}

        metrics = MetricsEngine.compute_all(db, ticket, sla_def, import_id)
        for m in metrics:
            db.add(m)
        db.commit()

        return {"metrics_written": len(metrics), "errors": []}

    @staticmethod
    def explain_ticket_sla(db: Session, ticket_id: int, import_id: str) -> dict:
        """Return a full SLA explanation for a ticket.

        Shows:
        - timeline breakdown
        - queue intervals with durations
        - owner intervals with durations
        - pending intervals with reasons
        - working intervals
        - where time was lost
        """
        explanation = explain_ticket_timeline(db, ticket_id, import_id)

        ticket = db.query(TicketSnapshot).filter(
            TicketSnapshot.ticket_id == ticket_id
        ).first()

        if ticket:
            sla_metrics = (
                db.query(SLAMetric)
                .filter(SLAMetric.ticket_id == ticket_id)
                .all()
            )
            explanation["metrics"] = [
                {
                    "name": m.metric_name,
                    "seconds": m.metric_seconds,
                    "breached": m.sla_breached,
                    "risk_level": m.risk_level,
                    "risk_score": m.risk_score,
                    "risk_reason": m.risk_reason,
                }
                for m in sla_metrics
            ]

        return explanation

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
