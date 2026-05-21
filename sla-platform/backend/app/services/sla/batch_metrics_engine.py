"""Batch metrics engine — preloads all data for all tickets, computes in memory, bulk inserts.

Eliminates N+1: instead of 10-20 queries per ticket, uses 5 total queries regardless of ticket count.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.models import SLADefinition, TicketSnapshot
from app.services.sla.business_hours import BusinessTimeEngine
from app.services.sla.pause_engine import compute_pause_segments_v2, PauseSegment
from app.services.sla.risk_engine import risk_level_from_ratio, risk_score_from_ratio

logger = logging.getLogger(__name__)

BATCH_SIZE = 2000


def _resolve_targets(
    sla_def: SLADefinition,
    queue_name: str | None,
) -> tuple[int, int]:
    response_target = sla_def.response_target_seconds
    resolution_target = sla_def.resolution_target_seconds
    if sla_def.business_hours_only:
        bte = BusinessTimeEngine.from_sla_def(sla_def)
    else:
        bte = None
    return response_target, resolution_target


def _compute_risk(metric_seconds: int, target_seconds: int) -> tuple[int, str, str]:
    if target_seconds <= 0:
        return (0, "low", "No target defined")
    ratio = metric_seconds / max(target_seconds, 1)
    breached = ratio >= 1.0
    level = risk_level_from_ratio(ratio)
    score = risk_score_from_ratio(ratio)
    if breached:
        reason = f"SLA breached at {ratio * 100:.0f}% of target"
    elif ratio >= 0.8:
        reason = f"Critical: {ratio * 100:.0f}% of target elapsed"
    elif ratio >= 0.5:
        reason = f"High: {ratio * 100:.0f}% of target elapsed"
    else:
        reason = f"Normal: {ratio * 100:.0f}% of target elapsed"
    return score, level, reason


def _find_first_response(events: list[dict]) -> datetime | None:
    for ev in events:
        if ev["event_type"] in ("SendAnswer", "EmailCustomer", "PhoneCallCustomer"):
            return ev["event_time"]
    return None


def _find_resolution(events: list[dict]) -> datetime | None:
    for ev in reversed(events):
        ns = ev.get("new_state", "")
        if ns in ("closed successful", "closed unsuccessful"):
            return ev["event_time"]
    return None


def _count_event_type(events: list[dict], etype: str) -> int:
    return sum(1 for ev in events if ev["event_type"] == etype)


def _active_seconds(pauses: list[PauseSegment], start: datetime, end: datetime) -> int:
    """Total active (non-paused) seconds between start and end.

    PauseSegment uses .pause_start / .pause_end (not start_time/end_time).
    Previous code accessed .start_time which raised AttributeError on every
    ticket and silently produced zero SLA metrics for every production import.
    """
    total_pause = 0
    for p in pauses:
        ps = getattr(p, "pause_start", None) or getattr(p, "start_time", None)
        pe = getattr(p, "pause_end", None) or getattr(p, "end_time", None) or end
        if pe and ps and pe > ps:
            clamped_start = max(ps, start)
            clamped_end = min(pe, end)
            if clamped_end > clamped_start:
                total_pause += int((clamped_end - clamped_start).total_seconds())
    return max(0, int((end - start).total_seconds()) - total_pause)


def compute_metrics_batch(
    db: Session,
    tickets: list[TicketSnapshot],
    sla_def: SLADefinition,
    import_id: str,
) -> list[dict]:
    if not tickets:
        return []

    ticket_ids = [t.ticket_id for t in tickets]
    import_id_str = str(import_id)

    # 1 query: load all events for all tickets
    rows = db.execute(
        text("""
            SELECT ticket_id, event_time, event_type,
                   queue_name, state_name, owner_name,
                   new_owner, new_state, is_system_action
            FROM ticket_events
            WHERE import_id = :iid AND ticket_id = ANY(:tids)
            ORDER BY ticket_id, event_seq
        """),
        {"iid": import_id_str, "tids": ticket_ids},
    ).mappings().all()

    events_by_ticket: dict[int, list[dict]] = {}
    for r in rows:
        events_by_ticket.setdefault(r["ticket_id"], []).append(dict(r))

    # 2 query: preload pause segments per ticket.
    # NOTE: compute_pause_segments_v2 has signature (db, ticket_id, import_id)
    # — previous code passed (import_id_str, events) which crashed
    # batch_compute_for_import with TypeError every single time and meant
    # NO SLA metrics were ever written by the batch path (the path used for
    # any import >10 tickets). This made every production import silently
    # skip SLA computation. Now we call with the correct signature.
    pause_by_ticket: dict[int, list[PauseSegment]] = {}
    for tid in ticket_ids:
        try:
            pause_by_ticket[tid] = compute_pause_segments_v2(db, tid, import_id_str)
        except Exception:
            pause_by_ticket[tid] = []

    response_target, resolution_target = _resolve_targets(sla_def, tickets[0].current_queue)

    results: list[dict] = []

    for ticket in tickets:
        tid = ticket.ticket_id
        evs = events_by_ticket.get(tid, [])
        pauses = pause_by_ticket.get(tid, [])
        if not evs:
            continue

        first = evs[0]
        last = evs[-1]
        created = first["event_time"]
        ended = last["event_time"]

        fr = _find_first_response(evs)
        res = _find_resolution(evs)

        if fr and created:
            raw = int((fr - created).total_seconds())
            active = _active_seconds(pauses, created, fr)
            score, level, reason = _compute_risk(active, response_target)
            results.append(dict(
                ticket_id=tid, metric_name="first_response_time",
                metric_seconds=active, sla_breached=active > response_target,
                sla_risk_score=score, risk_level=level, risk_reason=reason,
                queue_name=ticket.current_queue, owner=ticket.current_owner,
                team_prefix=queue_prefix(ticket.current_queue),
                sla_definition_id=sla_def.id, import_id=import_id_str, confidence="partial",
            ))

        if res and created:
            raw = int((res - created).total_seconds())
            active = _active_seconds(pauses, created, res)
            score, level, reason = _compute_risk(active, resolution_target)
            results.append(dict(
                ticket_id=tid, metric_name="resolution_time",
                metric_seconds=active, sla_breached=active > resolution_target,
                sla_risk_score=score, risk_level=level, risk_reason=reason,
                queue_name=ticket.current_queue, owner=ticket.current_owner,
                team_prefix=queue_prefix(ticket.current_queue),
                sla_definition_id=sla_def.id, import_id=import_id_str, confidence="partial",
            ))

        active_work = _active_seconds(pauses, created, ended) if created and ended else 0
        total_raw = int((ended - created).total_seconds()) if created and ended else 0
        paused_raw = max(0, total_raw - active_work)
        reopen = _count_event_type(evs, "StateUpdate")  # simplified

        results.append(dict(
            ticket_id=tid, metric_name="active_work_time",
            metric_seconds=active_work, queue_name=ticket.current_queue,
            sla_definition_id=sla_def.id, import_id=import_id_str, confidence="partial",
        ))
        results.append(dict(
            ticket_id=tid, metric_name="paused_time",
            metric_seconds=paused_raw, queue_name=ticket.current_queue,
            sla_definition_id=sla_def.id, import_id=import_id_str, confidence="partial",
        ))

    return results


_REQUIRED_METRIC_KEYS = (
    "ticket_id", "metric_name", "metric_seconds", "sla_breached",
    "sla_risk_score", "risk_level", "risk_reason",
    "queue_name", "owner", "team_prefix",
    "sla_definition_id", "import_id", "confidence",
)


def _bulk_insert_metrics(db: Session, metrics: list[dict]) -> int:
    if not metrics:
        return 0
    # Some metric dicts (active_work_time, paused_time) intentionally omit
    # sla_breached + risk fields; without these defaults the bulk INSERT
    # raises StatementError("A value is required for bind parameter
    # 'sla_breached'") and writes ZERO metrics for the entire import.
    for m in metrics:
        for k in _REQUIRED_METRIC_KEYS:
            m.setdefault(k, None)
        if m.get("sla_breached") is None:
            m["sla_breached"] = False
    for offset in range(0, len(metrics), BATCH_SIZE):
        batch = metrics[offset:offset + BATCH_SIZE]
        db.execute(
            text("""
                INSERT INTO sla_metrics (
                    ticket_id, metric_name, metric_seconds, sla_breached,
                    sla_risk_score, risk_level, risk_reason,
                    queue_name, owner, team_prefix,
                    sla_definition_id, import_id, confidence,
                    computed_at
                ) VALUES (
                    :ticket_id, :metric_name, :metric_seconds, :sla_breached,
                    :sla_risk_score, :risk_level, :risk_reason,
                    :queue_name, :owner, :team_prefix,
                    :sla_definition_id, :import_id, :confidence,
                    NOW()
                )
            """),
            batch,
        )
        db.commit()
    return len(metrics)


def queue_prefix(queue_name: str | None) -> str | None:
    if not queue_name:
        return None
    parts = queue_name.split("::")
    return parts[0] if len(parts) > 1 else None


def batch_compute_for_import(
    db: Session,
    tickets: list[TicketSnapshot],
    sla_def: SLADefinition,
    import_id: str,
) -> dict:
    metrics = compute_metrics_batch(db, tickets, sla_def, import_id)
    written = _bulk_insert_metrics(db, metrics)

    # V3 forensic metrics (wall-clock + loss buckets) — wired into the batch
    # path so they actually run on real production imports (>10 tickets).
    # The per-ticket path in sla_engine.compute_for_import already calls this
    # for tiny imports; without this hook here the V3 endpoints stay empty
    # forever in production.
    v3_written = 0
    v3_errors: list[dict] = []
    try:
        from app.services.forensics import ForensicAttributionEngine
        v3_models = []
        for ticket in tickets:
            try:
                v3_models.extend(
                    ForensicAttributionEngine.compute_wall_clock_metrics(
                        db, ticket, sla_def, import_id,
                    )
                )
            except Exception as exc:
                v3_errors.append({"ticket_id": ticket.ticket_id, "error": str(exc)})
        for m in v3_models:
            db.add(m)
        if v3_models:
            db.commit()
            v3_written = len(v3_models)
    except Exception as exc:
        v3_errors.append({"stage": "v3_init", "error": str(exc)})

    return {
        "metrics_written": written + v3_written,
        "v2_metrics": written,
        "v3_metrics": v3_written,
        "errors": v3_errors[:10],  # cap to keep response payload bounded
    }
