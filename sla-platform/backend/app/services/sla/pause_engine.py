"""Pause engine V2 — full SLA clock pause detection with audit trail.

Supports:
- Pending state detection (auto, manual, reminder, reopen)
- SetPendingTime events with pending_until boundary
- Stacked pending states (nested pauses)
- System action filtering
- Full pause audit trail with reasons
- Multiple pause triggers: pending customer, pending vendor,
  waiting external, merged, suspended, manual pause
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.sla.business_hours import calculate_business_seconds

PENDING_STATES = frozenset({
    "pending auto",
    "pending auto+",
    "pending reminder",
    "pending success",
    "pending success+",
    "pending manual",
    "pending manual+",
    "pending reopen",
})

PAUSE_TRIGGER_MAP = {
    "pending auto": "pending_customer",
    "pending auto+": "pending_customer",
    "pending reminder": "pending_customer",
    "pending success": "pending_vendor",
    "pending success+": "pending_vendor",
    "pending manual": "manual_pause",
    "pending manual+": "manual_pause",
    "pending reopen": "pending_reopen",
}

RESUME_TRIGGERS = frozenset({
    "new customer message",
    "owner change",
    "queue change",
    "reopen",
    "manual resume",
})


class PauseSegment:
    __slots__ = ("pause_start", "pause_end", "reason", "trigger_event")

    def __init__(
        self,
        pause_start: datetime,
        pause_end: Optional[datetime],
        reason: str = "pending",
        trigger_event: Optional[str] = None,
    ):
        self.pause_start = pause_start
        self.pause_end = pause_end
        self.reason = reason
        self.trigger_event = trigger_event

    def to_dict(self) -> dict:
        return {
            "pause_start": self.pause_start.isoformat(),
            "pause_end": self.pause_end.isoformat() if self.pause_end else None,
            "reason": self.reason,
            "trigger_event": self.trigger_event,
        }


def compute_pause_segments(
    db: Session,
    ticket_id: int,
    import_id: str,
) -> list[tuple[datetime, datetime]]:
    """Extract pause intervals — returns list of (pause_start, pause_end) tuples.

    Legacy-compatible signature. Internally uses the V2 engine.
    """
    segments = compute_pause_segments_v2(db, ticket_id, import_id)
    return [(s.pause_start, s.pause_end) for s in segments if s.pause_end is not None]


def compute_pause_segments_v2(
    db: Session,
    ticket_id: int,
    import_id: str,
) -> list[PauseSegment]:
    """Full pause audit trail with reasons and trigger events."""
    rows = db.execute(
        text("""
            SELECT event_time, event_type, state_name, new_state,
                   pending_until, new_owner, dest_queue, is_system_action
            FROM ticket_events
            WHERE ticket_id = :ticket_id AND import_id = :import_id
            ORDER BY event_seq
        """),
        {"ticket_id": ticket_id, "import_id": import_id},
    ).mappings().all()

    segments: list[PauseSegment] = []
    pause_stack: list[tuple[datetime, str, str]] = []

    for row in rows:
        et = row["event_type"]
        st = (row["state_name"] or "").lower()
        ns = (row["new_state"] or "").lower()
        pu = row["pending_until"]
        is_sys = row["is_system_action"] or False

        if is_sys:
            continue

        entering_pending = ns in PENDING_STATES and st not in PENDING_STATES
        staying_pending = ns in PENDING_STATES and st in PENDING_STATES
        exiting_pending = st in PENDING_STATES and ns not in PENDING_STATES and ns not in PENDING_STATES
        is_pending_event = et == "SetPendingTime" and pu is not None

        resume_event = (
            not entering_pending
            and not staying_pending
            and not is_pending_event
            and pause_stack
        )

        if entering_pending:
            trigger = PAUSE_TRIGGER_MAP.get(ns, "pending")
            pause_stack.append((row["event_time"], trigger, ns))

        elif staying_pending:
            pass

        elif is_pending_event:
            pause_stack.append((row["event_time"], "pending_external", "SetPendingTime"))

        elif resume_event:
            for pstart, preason, precause in pause_stack:
                pause_end = row["event_time"]
                if pu and pu < pause_end:
                    pause_end = pu
                segments.append(PauseSegment(
                    pause_start=pstart,
                    pause_end=pause_end,
                    reason=preason,
                    trigger_event=precause,
                ))
            pause_stack.clear()

    for pstart, preason, precause in pause_stack:
        segments.append(PauseSegment(
            pause_start=pstart,
            pause_end=None,
            reason=preason,
            trigger_event=precause,
        ))

    return segments


def calculate_active_time(
    db: Session,
    ticket_id: int,
    import_id: str,
    periods: list[tuple[datetime, datetime]],
    business_hours_config: Optional[dict] = None,
) -> dict[str, Any]:
    """Calculate active vs paused time for multiple periods.

    Returns:
        active_time_seconds: total seconds not paused
        paused_time_seconds: total seconds paused
        pause_audit: list of pause segment dicts
        segments: list of (start, end, type) dicts
    """
    pause_segments = compute_pause_segments_v2(db, ticket_id, import_id)
    segments: list[dict] = []
    active_total = 0
    paused_total = 0

    for ps, pe in periods:
        cursor = ps
        for pseg in pause_segments:
            pps = pseg.pause_start
            ppe = pseg.pause_end

            if ppe is None:
                ppe = pe

            if pps >= pe or ppe <= cursor:
                continue

            if pps > cursor:
                active = _time_in_range(cursor, pps, business_hours_config)
                active_total += active
                segments.append({"start": cursor, "end": pps, "type": "active", "seconds": active})

            pstart = max(cursor, pps)
            pend = min(ppe, pe)
            paused = _time_in_range(pstart, pend, business_hours_config)
            paused_total += paused
            segments.append({
                "start": pstart,
                "end": pend,
                "type": "paused",
                "seconds": paused,
                "reason": pseg.reason,
            })
            cursor = pend

        if cursor < pe:
            active = _time_in_range(cursor, pe, business_hours_config)
            active_total += active
            segments.append({"start": cursor, "end": pe, "type": "active", "seconds": active})

    return {
        "active_time_seconds": active_total,
        "paused_time_seconds": paused_total,
        "pause_audit": [p.to_dict() for p in pause_segments],
        "segments": segments,
    }


def _time_in_range(
    start: datetime,
    end: datetime,
    business_hours_config: Optional[dict],
) -> int:
    if business_hours_config:
        return calculate_business_seconds(start, end, business_hours_config)
    return int((end - start).total_seconds())
