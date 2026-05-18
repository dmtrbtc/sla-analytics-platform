"""Risk engine — detects tickets close to SLA breach before actual breach.

Risk levels based on elapsed_time / SLA_limit ratio:
  < 0.6   → LOW
  0.6–0.8 → MEDIUM
  0.8–0.95 → HIGH
  >= 0.95 → CRITICAL
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.models import SLADefinition, TicketSnapshot

logger = logging.getLogger(__name__)


def compute_risk_ratio(elapsed_seconds: int, target_seconds: int) -> float:
    """Return ratio of elapsed time to SLA target (0.0–1.0+)."""
    if target_seconds <= 0:
        return 0.0
    return elapsed_seconds / target_seconds


def risk_level_from_ratio(ratio: float) -> str:
    if ratio >= 0.95:
        return "critical"
    if ratio >= 0.80:
        return "high"
    if ratio >= 0.60:
        return "medium"
    return "low"


def risk_score_from_ratio(ratio: float) -> int:
    """0–100 score reflecting proximity to breach."""
    if ratio >= 1.0:
        return 100
    return min(100, int(ratio * 100))


def compute_ticket_risk(
    db: Session,
    ticket: TicketSnapshot,
    sla_def: SLADefinition,
    import_id: str,
) -> Optional[dict]:
    """Compute SLA risk for a single ticket.

    Checks both response and resolution SLA targets.
    Returns dict with risk details or None.
    """
    from app.services.sla.pause_engine import calculate_active_time

    bh_config = sla_def.business_hours if sla_def.business_hours_only else None

    # Check queue rule override
    from app.services.sla.metrics_engine import MetricsEngine
    queue_rule = MetricsEngine.resolve_sla_rule_by_queue(db, ticket.current_queue)
    response_target = queue_rule.response_target_seconds if queue_rule else sla_def.response_target_seconds
    resolution_target = queue_rule.resolution_target_seconds if queue_rule else sla_def.resolution_target_seconds

    risks = []

    if ticket.created_at and ticket.first_response_at:
        active = calculate_active_time(
            db, ticket.ticket_id, import_id,
            [(ticket.created_at, ticket.first_response_at)],
            bh_config,
        )
        elapsed = active["active_time_seconds"]
        ratio = compute_risk_ratio(elapsed, response_target)
        if ratio >= 0.60:
            risks.append({
                "metric": "response_time",
                "elapsed_seconds": elapsed,
                "target_seconds": response_target,
                "ratio": ratio,
                "risk_level": risk_level_from_ratio(ratio),
                "risk_score": risk_score_from_ratio(ratio),
                "reason": f"response_time at {ratio:.0%} of SLA limit",
            })

    if ticket.created_at and ticket.resolution_at:
        active = calculate_active_time(
            db, ticket.ticket_id, import_id,
            [(ticket.created_at, ticket.resolution_at)],
            bh_config,
        )
        elapsed = active["active_time_seconds"]
        ratio = compute_risk_ratio(elapsed, resolution_target)
        if ratio >= 0.60:
            risks.append({
                "metric": "resolution_time",
                "elapsed_seconds": elapsed,
                "target_seconds": resolution_target,
                "ratio": ratio,
                "risk_level": risk_level_from_ratio(ratio),
                "risk_score": risk_score_from_ratio(ratio),
                "reason": f"resolution_time at {ratio:.0%} of SLA limit",
            })

    if not risks:
        return None

    # Highest risk wins
    worst = max(risks, key=lambda r: r["risk_score"])
    return {
        "ticket_id": ticket.ticket_id,
        "queue_name": ticket.current_queue,
        "risk_level": worst["risk_level"],
        "risk_score": worst["risk_score"],
        "risk_reason": worst["reason"],
        "risks": risks,
    }


def compute_risks_for_import(db: Session, import_id: str) -> list[dict]:
    """Compute risk scores for all tickets in an import."""
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
        logger.warning("No active SLA definitions — using defaults")
        from app.services.sla_engine import SLAEngine
        sla_defs = [SLAEngine._default_sla_definition()]

    from app.services.sla.rule_engine import match_sla

    results = []
    for ticket in tickets:
        try:
            sla_def = match_sla(ticket, sla_defs)
            if not sla_def:
                continue
            risk = compute_ticket_risk(db, ticket, sla_def, import_id)
            if risk:
                results.append(risk)
        except Exception:
            logger.exception("Risk computation failed for ticket %s", ticket.ticket_id)

    return results


def get_active_risks(db: Session, limit: int = 50) -> list[dict]:
    """Return current high-risk tickets across all imports."""
    tickets = (
        db.query(TicketSnapshot)
        .filter(TicketSnapshot.is_closed == False)
        .order_by(TicketSnapshot.ticket_id.desc())
        .limit(200)
        .all()
    )
    sla_defs = (
        db.query(SLADefinition)
        .filter(SLADefinition.is_active == True)
        .all()
    )
    if not sla_defs:
        return []

    from app.services.sla.rule_engine import match_sla

    results = []
    for ticket in tickets:
        try:
            sla_def = match_sla(ticket, sla_defs)
            if not sla_def:
                continue
            import_id = str(ticket.last_import_id) if ticket.last_import_id else ""
            risk = compute_ticket_risk(db, ticket, sla_def, import_id)
            if risk and risk["risk_level"] in ("high", "critical"):
                results.append(risk)
                if len(results) >= limit:
                    break
        except Exception:
            continue

    return results
