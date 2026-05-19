"""Metrics engine — computes response, resolution, queue, and owner SLA metrics.

Every metric uses pause-engine and business-hours rules.
No raw datetime subtractions as final logic.
"""

import fnmatch
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.models import SLADefinition, SLAMetric, SLAQueueRule, TicketSnapshot
from app.services.sla.pause_engine import calculate_active_time, compute_pause_segments
from app.services.sla.business_hours import calculate_business_seconds

logger = logging.getLogger(__name__)

# Module-level cache for SLA queue rules (rarely changes)
_sla_queue_rules_cache: list[SLAQueueRule] | None = None
_sla_queue_rules_cache_ts: float = 0
_SLA_RULES_CACHE_TTL = 60  # seconds


def _get_active_queue_rules(db: Session) -> list[SLAQueueRule]:
    """Return cached active SLA queue rules, refreshing every TTL seconds."""
    global _sla_queue_rules_cache, _sla_queue_rules_cache_ts
    now = time.time()
    if _sla_queue_rules_cache is None or (now - _sla_queue_rules_cache_ts) > _SLA_RULES_CACHE_TTL:
        rules = (
            db.query(SLAQueueRule)
            .filter(SLAQueueRule.is_active == True)
            .order_by(SLAQueueRule.priority.desc().nullslast(), SLAQueueRule.created_at.asc())
            .all()
        )
        _sla_queue_rules_cache = rules
        _sla_queue_rules_cache_ts = now
    return _sla_queue_rules_cache


class MetricsEngine:

    @staticmethod
    def resolve_sla_rule_by_queue(
        db: Session,
        queue_name: Optional[str],
    ) -> Optional[SLAQueueRule]:
        """Find the best SLAQueueRule matching *queue_name*.

        First match wins, ordered by priority desc then creation date asc.
        Returns None if no rule matches (caller falls back to SLADefinition).
        """
        if not queue_name:
            return None
        rules = _get_active_queue_rules(db)
        for rule in rules:
            if fnmatch.fnmatch(queue_name, rule.queue_pattern):
                return rule
        return None

    @staticmethod
    def compute_all(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
    ) -> list[SLAMetric]:
        """Compute all SLA metrics for a single ticket and return ORM objects."""
        metrics: list[SLAMetric] = []

        pause_cache = compute_pause_segments(db, ticket.ticket_id, import_id)

        response = MetricsEngine.compute_response_time(db, ticket, sla_def, import_id, pause_cache)
        if response:
            metrics.append(response)

        resolution = MetricsEngine.compute_resolution_time(db, ticket, sla_def, import_id, pause_cache)
        if resolution:
            metrics.append(resolution)

        queue_metrics = MetricsEngine.compute_queue_time(db, ticket, sla_def, import_id, pause_cache)
        metrics.extend(queue_metrics)

        owner_metrics = MetricsEngine.compute_owner_time(db, ticket, sla_def, import_id, pause_cache)
        metrics.extend(owner_metrics)

        return metrics

    @staticmethod
    def compute_response_time(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        _pause_cache: Optional[list] = None,
    ) -> Optional[SLAMetric]:
        """Response time = time from creation to first response, excluding pauses."""
        if not ticket.created_at or not ticket.first_response_at:
            return None

        bh_config = sla_def.business_hours if sla_def.business_hours_only else None
        active = calculate_active_time(
            db, ticket.ticket_id, import_id,
            [(ticket.created_at, ticket.first_response_at)],
            bh_config,
        )

        effective = active["active_time_seconds"]
        queue_rule = MetricsEngine.resolve_sla_rule_by_queue(db, ticket.current_queue)
        target = queue_rule.response_target_seconds if queue_rule else sla_def.response_target_seconds
        breached = target > 0 and effective > target

        return SLAMetric(
            ticket_id=ticket.ticket_id,
            metric_name="response_time",
            metric_seconds=effective,
            sla_breached=breached,
            sla_definition_id=sla_def.id,
            import_id=UUID(import_id),
            queue_name=ticket.current_queue,
            owner=ticket.current_owner,
            confidence=ticket.confidence,
            computed_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def compute_resolution_time(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        _pause_cache: Optional[list] = None,
    ) -> Optional[SLAMetric]:
        """Resolution time = time from creation to resolution, excluding pauses."""
        if not ticket.created_at or not ticket.resolution_at:
            return None

        bh_config = sla_def.business_hours if sla_def.business_hours_only else None
        active = calculate_active_time(
            db, ticket.ticket_id, import_id,
            [(ticket.created_at, ticket.resolution_at)],
            bh_config,
        )

        effective = active["active_time_seconds"]
        queue_rule = MetricsEngine.resolve_sla_rule_by_queue(db, ticket.current_queue)
        target = queue_rule.resolution_target_seconds if queue_rule else sla_def.resolution_target_seconds
        breached = target > 0 and effective > target

        return SLAMetric(
            ticket_id=ticket.ticket_id,
            metric_name="resolution_time",
            metric_seconds=effective,
            sla_breached=breached,
            sla_definition_id=sla_def.id,
            import_id=UUID(import_id),
            queue_name=ticket.current_queue,
            owner=ticket.current_owner,
            confidence=ticket.confidence,
            computed_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def compute_queue_time(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        _pause_cache: Optional[list] = None,
    ) -> list[SLAMetric]:
        """Queue time breakdown — one metric per queue the ticket visited."""
        qperiods = db.execute(
            text(
                """
                SELECT queue_name, entered_at, exited_at
                FROM queue_periods
                WHERE ticket_id = :ticket_id
                ORDER BY entered_at
                """
            ),
            {"ticket_id": ticket.ticket_id},
        ).mappings().all()

        bh_config = sla_def.business_hours if sla_def.business_hours_only else None
        pause_segments = _pause_cache or compute_pause_segments(db, ticket.ticket_id, import_id)
        metrics: list[SLAMetric] = []

        for qp in qperiods:
            if not qp["entered_at"] or not qp["exited_at"]:
                continue
            qname = qp["queue_name"] or "unknown"
            period = (qp["entered_at"], qp["exited_at"])
            active = calculate_active_time(db, ticket.ticket_id, import_id, [period], bh_config)

            metrics.append(SLAMetric(
                ticket_id=ticket.ticket_id,
                metric_name="queue_time",
                metric_seconds=active["active_time_seconds"],
                sla_breached=False,
                sla_definition_id=sla_def.id,
                import_id=UUID(import_id),
                queue_name=qname,
                owner=ticket.current_owner,
                confidence=ticket.confidence,
                computed_at=datetime.now(timezone.utc),
            ))

        return metrics

    @staticmethod
    def compute_owner_time(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        _pause_cache: Optional[list] = None,
    ) -> list[SLAMetric]:
        """Owner time breakdown — one metric per owner who handled the ticket."""
        operiods = db.execute(
            text(
                """
                SELECT owner, start_time, end_time
                FROM ownership_periods
                WHERE ticket_id = :ticket_id
                ORDER BY start_time
                """
            ),
            {"ticket_id": ticket.ticket_id},
        ).mappings().all()

        bh_config = sla_def.business_hours if sla_def.business_hours_only else None
        pause_segments = _pause_cache or compute_pause_segments(db, ticket.ticket_id, import_id)
        metrics: list[SLAMetric] = []

        for op in operiods:
            if not op["start_time"] or not op["end_time"]:
                continue
            owner = op["owner"] or "unassigned"
            period = (op["start_time"], op["end_time"])
            active = calculate_active_time(db, ticket.ticket_id, import_id, [period], bh_config)

            metrics.append(SLAMetric(
                ticket_id=ticket.ticket_id,
                metric_name="owner_time",
                metric_seconds=active["active_time_seconds"],
                sla_breached=False,
                sla_definition_id=sla_def.id,
                import_id=UUID(import_id),
                queue_name=ticket.current_queue,
                owner=owner,
                confidence=ticket.confidence,
                computed_at=datetime.now(timezone.utc),
            ))

        return metrics
