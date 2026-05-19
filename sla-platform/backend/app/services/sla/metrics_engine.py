"""Metrics engine V2 — enterprise SLA metrics computation.

Metrics:
- first_response_time: creation → first owner response (minus pauses)
- resolution_time: creation → final resolution (minus pauses)
- assignment_time: creation → first owner assignment
- queue_wait_time: per-queue active wait
- active_work_time: total non-paused ticket time
- paused_time: total paused time
- customer_wait_time: time in pending-customer states
- vendor_wait_time: time in pending-vendor states
- reopen_count: number of post-resolution reopens
- reassignment_count: number of owner changes
- queue_bounce_count: number of queue transitions
- escalation_count: number of escalation events
- ownership_changes: total owner handoffs
- touch_count: total non-system events
- response_breach_delta: seconds over/below response target
- resolution_breach_delta: seconds over/below resolution target

Efficiency metrics:
- sla_efficiency_pct: 100 * (1 - paused / total)
- wasted_time_pct: 100 * paused / total
- active_work_ratio: active work / total active
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
from app.services.sla.pause_engine import calculate_active_time, compute_pause_segments, compute_pause_segments_v2
from app.services.sla.business_hours import calculate_business_seconds

logger = logging.getLogger(__name__)

_sla_queue_rules_cache: list[SLAQueueRule] | None = None
_sla_queue_rules_cache_ts: float = 0
_SLA_RULES_CACHE_TTL = 60


def _get_active_queue_rules(db: Session) -> list[SLAQueueRule]:
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


def _resolve_breach_target(
    db: Session,
    ticket: TicketSnapshot,
    sla_def: SLADefinition,
    target_field: str,
) -> int:
    """Resolve target seconds: queue rule override or SLA definition default."""
    if not ticket.current_queue:
        return getattr(sla_def, target_field, 0)
    rules = _get_active_queue_rules(db)
    for rule in rules:
        if fnmatch.fnmatch(ticket.current_queue, rule.queue_pattern):
            rule_target = getattr(rule, target_field, None)
            if rule_target is not None:
                return rule_target
    return getattr(sla_def, target_field, 0)


def _compute_risk_level(effective: int, target: int) -> tuple[Optional[int], Optional[str], Optional[str]]:
    """Compute SLA risk score, level, and reason."""
    if target <= 0:
        return (None, None, None)
    ratio = effective / target
    if ratio >= 1.0:
        score = min(100, int(ratio * 100))
        return (score, "breached", f"SLA breached at {ratio:.0%} of target")
    if ratio >= 0.95:
        return (95, "critical", f"{ratio:.0%} of target elapsed")
    if ratio >= 0.80:
        return (int(ratio * 100), "high", f"{ratio:.0%} of target elapsed")
    if ratio >= 0.60:
        return (int(ratio * 100), "medium", f"{ratio:.0%} of target elapsed")
    return (None, None, None)


def _compute_efficiency(paused: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return round(100.0 * (1.0 - paused / max(total, 1)), 1)


class MetricsEngine:

    @staticmethod
    def resolve_sla_rule_by_queue(
        db: Session,
        queue_name: Optional[str],
    ) -> Optional[SLAQueueRule]:
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
        metrics: list[SLAMetric] = []
        pause_cache = compute_pause_segments(db, ticket.ticket_id, import_id)

        m = MetricsEngine.compute_first_response_time(db, ticket, sla_def, import_id, pause_cache)
        if m:
            metrics.append(m)

        m = MetricsEngine.compute_resolution_time(db, ticket, sla_def, import_id, pause_cache)
        if m:
            metrics.append(m)

        m = MetricsEngine.compute_assignment_time(db, ticket, sla_def, import_id)
        if m:
            metrics.append(m)

        queue_metrics = MetricsEngine.compute_queue_time(db, ticket, sla_def, import_id, pause_cache)
        metrics.extend(queue_metrics)

        owner_metrics = MetricsEngine.compute_owner_time(db, ticket, sla_def, import_id, pause_cache)
        metrics.extend(owner_metrics)

        m = MetricsEngine.compute_active_work_time(db, ticket, sla_def, import_id, pause_cache)
        if m:
            metrics.append(m)

        m = MetricsEngine.compute_paused_time_metric(db, ticket, sla_def, import_id)
        if m:
            metrics.append(m)

        m = MetricsEngine.compute_reopen_count(db, ticket, sla_def, import_id)
        if m:
            metrics.append(m)

        m = MetricsEngine.compute_reassignment_count(db, ticket, sla_def, import_id)
        if m:
            metrics.append(m)

        m = MetricsEngine.compute_queue_bounce_count(db, ticket, sla_def, import_id)
        if m:
            metrics.append(m)

        m = MetricsEngine.compute_touch_count(db, ticket, sla_def, import_id)
        if m:
            metrics.append(m)

        m = MetricsEngine.compute_sla_efficiency(db, ticket, sla_def, import_id, pause_cache)
        if m:
            metrics.append(m)

        return metrics

    @staticmethod
    def _build_metric(
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        metric_name: str,
        metric_seconds: int,
        sla_breached: bool = False,
        queue_name: Optional[str] = None,
        owner: Optional[str] = None,
        team_prefix: Optional[str] = None,
        risk_score: Optional[int] = None,
        risk_level: Optional[str] = None,
        risk_reason: Optional[str] = None,
        confidence: Optional[str] = None,
    ) -> SLAMetric:
        return SLAMetric(
            ticket_id=ticket.ticket_id,
            metric_name=metric_name,
            metric_seconds=metric_seconds,
            sla_breached=sla_breached,
            sla_risk_score=risk_score,
            risk_level=risk_level,
            risk_reason=risk_reason,
            sla_definition_id=sla_def.id,
            import_id=UUID(import_id),
            queue_name=queue_name or ticket.current_queue,
            owner=owner or ticket.current_owner,
            team_prefix=team_prefix,
            confidence=confidence or ticket.confidence,
            computed_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def compute_first_response_time(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        _pause_cache: Optional[list] = None,
    ) -> Optional[SLAMetric]:
        if not ticket.created_at or not ticket.first_response_at:
            return None
        bh_config = sla_def.business_hours if sla_def.business_hours_only else None
        active = calculate_active_time(
            db, ticket.ticket_id, import_id,
            [(ticket.created_at, ticket.first_response_at)],
            bh_config,
        )
        effective = active["active_time_seconds"]
        target = _resolve_breach_target(db, ticket, sla_def, "response_target_seconds")
        breached = target > 0 and effective > target
        risk_score, risk_level, risk_reason = _compute_risk_level(effective, target)

        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="first_response_time",
            metric_seconds=effective,
            sla_breached=breached,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_reason=risk_reason,
        )

    @staticmethod
    def compute_resolution_time(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        _pause_cache: Optional[list] = None,
    ) -> Optional[SLAMetric]:
        if not ticket.created_at or not ticket.resolution_at:
            return None
        bh_config = sla_def.business_hours if sla_def.business_hours_only else None
        active = calculate_active_time(
            db, ticket.ticket_id, import_id,
            [(ticket.created_at, ticket.resolution_at)],
            bh_config,
        )
        effective = active["active_time_seconds"]
        target = _resolve_breach_target(db, ticket, sla_def, "resolution_target_seconds")
        breached = target > 0 and effective > target
        risk_score, risk_level, risk_reason = _compute_risk_level(effective, target)

        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="resolution_time",
            metric_seconds=effective,
            sla_breached=breached,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_reason=risk_reason,
        )

    @staticmethod
    def compute_assignment_time(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
    ) -> Optional[SLAMetric]:
        if not ticket.created_at:
            return None
        first_owner = db.execute(
            text("""
                SELECT MIN(start_time) as assigned_at
                FROM ownership_periods
                WHERE ticket_id = :ticket_id AND owner IS NOT NULL
            """),
            {"ticket_id": ticket.ticket_id},
        ).scalar()

        if not first_owner:
            return None

        effective = int((first_owner - ticket.created_at).total_seconds())
        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="assignment_time",
            metric_seconds=max(effective, 0),
        )

    @staticmethod
    def compute_queue_time(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        _pause_cache: Optional[list] = None,
    ) -> list[SLAMetric]:
        qperiods = db.execute(
            text("""
                SELECT queue_name, entered_at, exited_at, team_prefix
                FROM queue_periods
                WHERE ticket_id = :ticket_id
                ORDER BY entered_at
            """),
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

            metrics.append(MetricsEngine._build_metric(
                ticket, sla_def, import_id,
                metric_name="queue_time",
                metric_seconds=active["active_time_seconds"],
                queue_name=qname,
                team_prefix=qp.get("team_prefix") or None,
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
        operiods = db.execute(
            text("""
                SELECT owner, start_time, end_time, team_prefix
                FROM ownership_periods
                WHERE ticket_id = :ticket_id
                ORDER BY start_time
            """),
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

            metrics.append(MetricsEngine._build_metric(
                ticket, sla_def, import_id,
                metric_name="owner_time",
                metric_seconds=active["active_time_seconds"],
                owner=owner,
                team_prefix=op.get("team_prefix") or None,
            ))

        return metrics

    @staticmethod
    def compute_active_work_time(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        _pause_cache: Optional[list] = None,
    ) -> Optional[SLAMetric]:
        end = ticket.resolution_at or ticket.updated_at or datetime.now(timezone.utc)
        if not ticket.created_at:
            return None
        bh_config = sla_def.business_hours if sla_def.business_hours_only else None
        active = calculate_active_time(
            db, ticket.ticket_id, import_id,
            [(ticket.created_at, end)],
            bh_config,
        )
        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="active_work_time",
            metric_seconds=active["active_time_seconds"],
        )

    @staticmethod
    def compute_paused_time_metric(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
    ) -> Optional[SLAMetric]:
        end = ticket.resolution_at or ticket.updated_at or datetime.now(timezone.utc)
        if not ticket.created_at:
            return None
        bh_config = sla_def.business_hours if sla_def.business_hours_only else None
        active = calculate_active_time(
            db, ticket.ticket_id, import_id,
            [(ticket.created_at, end)],
            bh_config,
        )
        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="paused_time",
            metric_seconds=active["paused_time_seconds"],
        )

    @staticmethod
    def compute_reopen_count(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
    ) -> Optional[SLAMetric]:
        count = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_events
                WHERE ticket_id = :ticket_id AND import_id = :import_id
                AND LOWER(event_type) LIKE '%reopen%'
            """),
            {"ticket_id": ticket.ticket_id, "import_id": import_id},
        ).scalar() or 0
        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="reopen_count",
            metric_seconds=count,
        )

    @staticmethod
    def compute_reassignment_count(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
    ) -> Optional[SLAMetric]:
        count = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_events
                WHERE ticket_id = :ticket_id AND import_id = :import_id
                AND new_owner IS NOT NULL AND old_owner IS NOT NULL
                AND new_owner != old_owner
            """),
            {"ticket_id": ticket.ticket_id, "import_id": import_id},
        ).scalar() or 0
        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="reassignment_count",
            metric_seconds=count,
        )

    @staticmethod
    def compute_queue_bounce_count(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
    ) -> Optional[SLAMetric]:
        count = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_events
                WHERE ticket_id = :ticket_id AND import_id = :import_id
                AND src_queue IS NOT NULL AND dest_queue IS NOT NULL
                AND src_queue != dest_queue
            """),
            {"ticket_id": ticket.ticket_id, "import_id": import_id},
        ).scalar() or 0
        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="queue_bounce_count",
            metric_seconds=count,
        )

    @staticmethod
    def compute_touch_count(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
    ) -> Optional[SLAMetric]:
        count = db.execute(
            text("""
                SELECT COUNT(*) FROM ticket_events
                WHERE ticket_id = :ticket_id AND import_id = :import_id
                AND (is_system_action IS NULL OR is_system_action = False)
            """),
            {"ticket_id": ticket.ticket_id, "import_id": import_id},
        ).scalar() or 0
        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="touch_count",
            metric_seconds=count,
        )

    @staticmethod
    def compute_sla_efficiency(
        db: Session,
        ticket: TicketSnapshot,
        sla_def: SLADefinition,
        import_id: str,
        _pause_cache: Optional[list] = None,
    ) -> Optional[SLAMetric]:
        end = ticket.resolution_at or ticket.updated_at or datetime.now(timezone.utc)
        if not ticket.created_at:
            return None
        bh_config = sla_def.business_hours if sla_def.business_hours_only else None
        active = calculate_active_time(
            db, ticket.ticket_id, import_id,
            [(ticket.created_at, end)],
            bh_config,
        )
        total = active["active_time_seconds"] + active["paused_time_seconds"]
        if total <= 0:
            return None
        efficiency_pct = _compute_efficiency(active["paused_time_seconds"], total)
        return MetricsEngine._build_metric(
            ticket, sla_def, import_id,
            metric_name="sla_efficiency_pct",
            metric_seconds=int(efficiency_pct * 100),
        )
