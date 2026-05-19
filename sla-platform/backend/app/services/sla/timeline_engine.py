"""Timeline Engine — reconstructs full ticket lifecycle from raw events.

Produces ordered, deduplicated, normalized intervals:
- queue intervals (entered/exited per queue)
- owner intervals (start/end per owner)
- pending intervals (pause start/end with reason)
- working intervals (active SLA clock periods)
- breached intervals (over-target segments)
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

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


class TimelineInterval:
    __slots__ = ("start", "end", "type", "label", "metadata")

    def __init__(
        self,
        start: datetime,
        end: Optional[datetime],
        interval_type: str,
        label: str = "",
        metadata: Optional[dict] = None,
    ):
        self.start = start
        self.end = end
        self.type = interval_type
        self.label = label
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "type": self.type,
            "label": self.label,
            "metadata": self.metadata,
        }

    def duration_seconds(self) -> Optional[float]:
        if self.end:
            return (self.end - self.start).total_seconds()
        return None


class TicketTimeline:
    """Reconstructed full lifecycle of a single ticket."""

    def __init__(self, ticket_id: int, import_id: str):
        self.ticket_id = ticket_id
        self.import_id = import_id
        self.intervals: list[TimelineInterval] = []
        self.events: list[dict] = []
        self.queue_intervals: list[TimelineInterval] = []
        self.owner_intervals: list[TimelineInterval] = []
        self.pending_intervals: list[TimelineInterval] = []
        self.working_intervals: list[TimelineInterval] = []


def build_timeline(db: Session, ticket_id: int, import_id: str) -> TicketTimeline:
    """Fetch events and reconstruct the full ticket timeline."""
    rows = db.execute(
        text("""
            SELECT event_seq, event_time, event_type, queue_name,
                   state_name, owner_name, new_state, new_owner,
                   old_state, old_owner, src_queue, dest_queue,
                   pending_until, is_system_action
            FROM ticket_events
            WHERE ticket_id = :ticket_id AND import_id = :import_id
            ORDER BY event_seq ASC, event_time ASC
        """),
        {"ticket_id": ticket_id, "import_id": import_id},
    ).mappings().all()

    timeline = TicketTimeline(ticket_id, import_id)

    if not rows:
        return timeline

    events = [_normalize_event(r) for r in rows]
    events = _deduplicate_events(events)
    timeline.events = events

    timeline.queue_intervals = _build_queue_intervals(events)
    timeline.owner_intervals = _build_owner_intervals(events)
    timeline.pending_intervals = _build_pending_intervals(events)
    timeline.working_intervals = _build_working_intervals(
        events, timeline.pending_intervals
    )

    timeline.intervals = (
        timeline.queue_intervals
        + timeline.owner_intervals
        + timeline.pending_intervals
        + timeline.working_intervals
    )

    return timeline


def _normalize_event(row: dict) -> dict:
    return {
        "event_seq": row["event_seq"],
        "event_time": row["event_time"],
        "event_type": row["event_type"],
        "queue_name": row["queue_name"],
        "state_name": (row["state_name"] or "").lower(),
        "owner_name": row["owner_name"],
        "new_state": (row["new_state"] or "").lower(),
        "new_owner": row["new_owner"],
        "old_state": (row["old_state"] or "").lower(),
        "old_owner": row["old_owner"],
        "src_queue": row["src_queue"],
        "dest_queue": row["dest_queue"],
        "pending_until": row["pending_until"],
        "is_system_action": row["is_system_action"] or False,
    }


def _deduplicate_events(events: list[dict]) -> list[dict]:
    """Remove consecutive duplicate events (same type, same state)."""
    if not events:
        return events
    deduped = [events[0]]
    for e in events[1:]:
        last = deduped[-1]
        if (
            e["event_type"] == last["event_type"]
            and e["new_state"] == last["new_state"]
            and e["queue_name"] == last["queue_name"]
            and e["owner_name"] == last["owner_name"]
        ):
            continue
        deduped.append(e)
    return deduped


def _build_queue_intervals(events: list[dict]) -> list[TimelineInterval]:
    """Extract queue entry/exit intervals from events."""
    intervals: list[TimelineInterval] = []
    current_queue: Optional[str] = None
    current_start: Optional[datetime] = None

    for e in events:
        q = e["queue_name"]
        if q and q != current_queue:
            if current_queue is not None and current_start is not None:
                intervals.append(TimelineInterval(
                    start=current_start,
                    end=e["event_time"],
                    interval_type="queue",
                    label=current_queue,
                ))
            current_queue = q
            current_start = e["event_time"]

    if current_queue is not None and current_start is not None:
        intervals.append(TimelineInterval(
            start=current_start,
            end=None,
            interval_type="queue",
            label=current_queue,
        ))

    return _merge_adjacent_intervals(intervals)


def _build_owner_intervals(events: list[dict]) -> list[TimelineInterval]:
    """Extract owner assignment intervals from events."""
    intervals: list[TimelineInterval] = []
    current_owner: Optional[str] = None
    current_start: Optional[datetime] = None

    for e in events:
        o = e["owner_name"] or e["new_owner"]
        if o and o != current_owner:
            if current_owner is not None and current_start is not None:
                intervals.append(TimelineInterval(
                    start=current_start,
                    end=e["event_time"],
                    interval_type="owner",
                    label=current_owner,
                ))
            current_owner = o
            current_start = e["event_time"]

    if current_owner is not None and current_start is not None:
        intervals.append(TimelineInterval(
            start=current_start,
            end=None,
            interval_type="owner",
            label=current_owner,
        ))

    return _merge_adjacent_intervals(intervals)


def _build_pending_intervals(events: list[dict]) -> list[TimelineInterval]:
    """Extract pending/pause intervals from events."""
    intervals: list[TimelineInterval] = []
    pause_start: Optional[datetime] = None
    pause_reason: Optional[str] = None
    in_pending = False

    for e in events:
        st = e["state_name"]
        ns = e["new_state"]
        et = e["event_type"]
        pu = e["pending_until"]

        is_pending = st in PENDING_STATES or ns in PENDING_STATES
        is_pending_event = et == "SetPendingTime" and pu is not None

        if is_pending or is_pending_event:
            if not in_pending:
                pause_start = e["event_time"]
                pause_reason = st if st in PENDING_STATES else ns
                in_pending = True
        else:
            if in_pending and pause_start is not None:
                pause_end = e["event_time"]
                if pu and pu < pause_end:
                    pause_end = pu
                intervals.append(TimelineInterval(
                    start=pause_start,
                    end=pause_end,
                    interval_type="pending",
                    label=pause_reason or "pending",
                    metadata={"reason": pause_reason},
                ))
                in_pending = False
                pause_start = None
                pause_reason = None

    if in_pending and pause_start is not None:
        intervals.append(TimelineInterval(
            start=pause_start,
            end=None,
            interval_type="pending",
            label=pause_reason or "pending",
            metadata={"reason": pause_reason},
        ))

    return intervals


def _build_working_intervals(
    events: list[dict],
    pending_intervals: list[TimelineInterval],
) -> list[TimelineInterval]:
    """Build active SLA-clock intervals (time NOT in pending)."""
    if not events:
        return []

    start = events[0]["event_time"]
    end = events[-1]["event_time"]

    working: list[TimelineInterval] = []
    cursor = start

    for pi in pending_intervals:
        pi_start = pi.start
        pi_end = pi.end or end

        if pi_start > cursor:
            working.append(TimelineInterval(
                start=cursor,
                end=pi_start,
                interval_type="working",
                label="active",
            ))
        cursor = max(cursor, pi_end)

    if cursor < end:
        working.append(TimelineInterval(
            start=cursor,
            end=end,
            interval_type="working",
            label="active",
        ))

    return working


def _merge_adjacent_intervals(intervals: list[TimelineInterval]) -> list[TimelineInterval]:
    """Merge adjacent intervals with the same label."""
    if not intervals:
        return intervals

    merged = [intervals[0]]
    for iv in intervals[1:]:
        last = merged[-1]
        if last.label == iv.label and last.type == iv.type:
            last.end = iv.end
        else:
            merged.append(iv)
    return merged


def explain_ticket_timeline(db: Session, ticket_id: int, import_id: str) -> dict:
    """Return a human-readable explanation of the ticket's SLA timeline."""
    timeline = build_timeline(db, ticket_id, import_id)

    return {
        "ticket_id": ticket_id,
        "total_intervals": len(timeline.intervals),
        "queue_intervals": len(timeline.queue_intervals),
        "owner_intervals": len(timeline.owner_intervals),
        "pending_intervals": len(timeline.pending_intervals),
        "working_intervals": len(timeline.working_intervals),
        "intervals": [iv.to_dict() for iv in timeline.intervals],
    }
