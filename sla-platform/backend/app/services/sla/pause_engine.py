"""Pause engine — detects SLA-clock pause intervals from ticket events.

Pauses occur during:
- "pending" states (pending-auto, pending-reminder, pending-success, etc.)
- SetPendingTime events
- System actions (if flagged)

Output: list of (pause_start, pause_end) tuples and summary stats.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

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


def compute_pause_segments(
    db: Session,
    ticket_id: int,
    import_id: str,
) -> list[tuple[datetime, datetime]]:
    """Extract pause intervals for a ticket by scanning TicketEvent state transitions.

    Returns ordered list of (pause_start, pause_end) segments.
    """
    rows = db.execute(
        text(
            """
            SELECT event_time, event_type, state_name, new_state, pending_until
            FROM ticket_events
            WHERE ticket_id = :ticket_id AND import_id = :import_id
            ORDER BY event_seq
            """
        ),
        {"ticket_id": ticket_id, "import_id": import_id},
    ).mappings().all()

    pauses: list[tuple[datetime, datetime]] = []
    pause_start: Optional[datetime] = None
    in_pending = False

    for row in rows:
        et = row["event_type"]
        st = row["state_name"] or ""
        ns = row["new_state"] or ""
        pending_until = row["pending_until"]

        is_pending = st.lower() in PENDING_STATES or ns.lower() in PENDING_STATES
        is_pending_event = et == "SetPendingTime" and pending_until is not None

        if is_pending or is_pending_event:
            if not in_pending:
                pause_start = row["event_time"]
                in_pending = True
        else:
            if in_pending and pause_start is not None:
                pauses.append((pause_start, row["event_time"]))
                in_pending = False
                pause_start = None

    if in_pending and pause_start is not None:
        pauses.append((pause_start, rows[-1]["event_time"] if rows else pause_start))

    return pauses


def calculate_active_time(
    db: Session,
    ticket_id: int,
    import_id: str,
    periods: list[tuple[datetime, datetime]],
    business_hours_config: Optional[dict] = None,
) -> dict[str, Any]:
    """Calculate active vs paused time for a ticket's duration periods.

    Returns:
        active_time_seconds: total time not paused
        paused_time_seconds: total paused time
        segments: list of (start, end, type)
    """
    from app.services.sla.business_hours import calculate_business_seconds

    pause_segments = compute_pause_segments(db, ticket_id, import_id)
    segments: list[dict] = []
    active_total = 0
    paused_total = 0

    for ps, pe in periods:
        cursor = ps
        for pps, ppe in pause_segments:
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
            segments.append({"start": pstart, "end": pend, "type": "paused", "seconds": paused})
            cursor = pend
        if cursor < pe:
            active = _time_in_range(cursor, pe, business_hours_config)
            active_total += active
            segments.append({"start": cursor, "end": pe, "type": "active", "seconds": active})

    return {
        "active_time_seconds": active_total,
        "paused_time_seconds": paused_total,
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
