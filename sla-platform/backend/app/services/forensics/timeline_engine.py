"""Forensic queue timeline — Phase 2 v1.7.

For a single ticket, reconstruct the full queue journey with per-queue:
  - entered_at / exited_at / minutes_in_queue
  - response_timer_running   (True only on the segment containing the
                               first response. After the first response,
                               the response timer is permanently stopped.)
  - resolution_timer_running (True for every segment until resolution_at)
  - owner_during_segment     (most-active owner)
  - paused                   (any pending-state event inside this segment)
  - no_owner_minutes         (segment time owned by root@localhost or null)
  - response_loss_minutes    (segment time that counted toward the
                               response SLA — zero after first response)
  - resolution_loss_minutes  (segment time that counted toward the
                               resolution SLA — zero after resolution_at)
  - queue_contribution_pct   (segment_minutes / total_minutes × 100)

Plus a root_cause section that names:
  - breach_queue, breach_at
  - response_passed_in_queue (where the response was delivered)
  - top_loss_queue (largest resolution_loss_minutes)
  - bounces (queues visited >= 2x)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


SYS_OWNER_SET = {"", "root@localhost", "otrs admin (root@localhost)"}


def _is_sys(owner: Optional[str]) -> bool:
    if owner is None:
        return True
    return owner.strip().lower() in SYS_OWNER_SET


@dataclass
class TimelineSegment:
    queue_name: str
    entered_at: str
    exited_at: Optional[str]
    minutes_in_queue: int
    response_timer_running: bool
    resolution_timer_running: bool
    paused: bool
    no_owner_minutes: int
    response_loss_minutes: int
    resolution_loss_minutes: int
    owners_during: list[dict[str, Any]]
    breach_inside_segment: bool
    queue_contribution_pct: float


class TimelineEngine:

    @staticmethod
    def for_ticket(
        db: Session,
        ticket_id: int,
        response_target_seconds: int = 1800,
        resolution_target_seconds: int = 28800,
    ) -> dict[str, Any]:
        # ---- ticket meta -----------------------------------------------
        t = db.execute(
            text("""
                SELECT ticket_id, ticket_number, title,
                       created_at, first_response_at, resolution_at,
                       current_queue, current_state, current_owner,
                       is_closed
                FROM ticket_snapshots WHERE ticket_id = :tid
            """),
            {"tid": ticket_id},
        ).mappings().first()
        if not t:
            return {"error": "Ticket not found"}

        # ---- queue periods (ordered) ----------------------------------
        qp = db.execute(
            text("""
                SELECT queue_name, entered_at, exited_at,
                       COALESCE(duration_seconds,
                                EXTRACT(EPOCH FROM
                                  (COALESCE(exited_at, NOW()) - entered_at)))::bigint AS dur_sec
                FROM queue_periods WHERE ticket_id = :tid
                ORDER BY entered_at
            """),
            {"tid": ticket_id},
        ).mappings().all()
        if not qp:
            return {
                "ticket": dict(t),
                "segments": [],
                "summary": {"total_minutes": 0, "message": "no queue periods reconstructed"},
            }

        # ---- ownership periods (for "owner during segment") -----------
        op = db.execute(
            text("""
                SELECT owner, queue_name, start_time, end_time,
                       EXTRACT(EPOCH FROM
                         (COALESCE(end_time, NOW()) - start_time))::bigint AS dur_sec
                FROM ownership_periods WHERE ticket_id = :tid
                ORDER BY start_time
            """),
            {"tid": ticket_id},
        ).mappings().all()

        # ---- pause events: state names containing 'pending' -----------
        pause_evts = db.execute(
            text("""
                SELECT event_time, queue_name, state_name
                FROM ticket_events
                WHERE ticket_id = :tid
                  AND state_name ILIKE 'pending%'
                ORDER BY event_time
            """),
            {"tid": ticket_id},
        ).mappings().all()
        pause_set = {(p["queue_name"], p["event_time"]) for p in pause_evts}

        # ---- iterate segments ------------------------------------------
        first_resp = t["first_response_at"]
        resolution = t["resolution_at"]
        total_sec = sum(int(s["dur_sec"] or 0) for s in qp) or 1

        segments: list[TimelineSegment] = []
        for seg in qp:
            entered = seg["entered_at"]
            exited = seg["exited_at"] or datetime.now(timezone.utc).replace(tzinfo=None)
            dur_sec = int(seg["dur_sec"] or 0)
            minutes = max(0, dur_sec // 60)
            queue_name = seg["queue_name"] or "unknown"

            # response_timer_running on this segment:
            # True if NO first_response_at OR first_response_at falls within this segment
            response_running = (
                first_resp is None
                or (first_resp >= entered and first_resp <= exited)
                or (first_resp > exited)  # first response not yet delivered → still running
            )
            # response_loss is time spent on response SLA before first_resp
            if first_resp is None:
                # Whole segment counts toward (still-running) response
                response_loss_sec = dur_sec
            elif first_resp <= entered:
                response_loss_sec = 0   # response already delivered before this segment
            else:
                # response delivered partway through (or in a later segment)
                end_for_resp = min(first_resp, exited)
                response_loss_sec = max(0, int((end_for_resp - entered).total_seconds()))

            # resolution_timer_running: True until resolution_at
            resolution_running = (
                resolution is None
                or (resolution >= entered and resolution <= exited)
                or (resolution > exited)
            )
            if resolution is None:
                resolution_loss_sec = dur_sec
            elif resolution <= entered:
                resolution_loss_sec = 0
            else:
                end_for_resol = min(resolution, exited)
                resolution_loss_sec = max(0, int((end_for_resol - entered).total_seconds()))

            # owners during this segment (intersect ownership periods)
            owners_in_segment: list[dict] = []
            no_owner_sec = 0
            for o in op:
                o_start = o["start_time"]
                o_end = o["end_time"] or datetime.now(timezone.utc).replace(tzinfo=None)
                # intersection
                lo = max(o_start, entered)
                hi = min(o_end, exited)
                if hi > lo:
                    overlap_sec = int((hi - lo).total_seconds())
                    owners_in_segment.append({
                        "owner": o["owner"] or "—",
                        "seconds": overlap_sec,
                        "is_system": _is_sys(o["owner"]),
                    })
                    if _is_sys(o["owner"]):
                        no_owner_sec += overlap_sec

            # paused: did any pending* event happen in [entered, exited]?
            paused = any(
                (queue_name == p_q or p_q is None)
                and entered <= p_t <= exited
                for (p_q, p_t) in pause_set
            )

            # breach detection inside segment:
            # resolution deadline = created_at + resolution_target_seconds
            breach_inside = False
            if t["created_at"]:
                deadline = t["created_at"] + timedelta(seconds=resolution_target_seconds)
                if entered <= deadline <= exited:
                    breach_inside = True

            segments.append(TimelineSegment(
                queue_name=queue_name,
                entered_at=entered.isoformat() if entered else None,
                exited_at=seg["exited_at"].isoformat() if seg["exited_at"] else None,
                minutes_in_queue=minutes,
                response_timer_running=response_running,
                resolution_timer_running=resolution_running,
                paused=paused,
                no_owner_minutes=no_owner_sec // 60,
                response_loss_minutes=response_loss_sec // 60,
                resolution_loss_minutes=resolution_loss_sec // 60,
                owners_during=owners_in_segment,
                breach_inside_segment=breach_inside,
                queue_contribution_pct=round(dur_sec / total_sec * 100, 2),
            ))

        # ---- summary ---------------------------------------------------
        total_minutes = total_sec // 60

        # FIRST-RESPONSE RULE INVARIANT:
        # "Once the first response is delivered, response SLA timer must
        # stop permanently — no later segment may contribute response loss."
        #
        # In segment terms:
        #   - segments BEFORE first_response_at  → full duration counts toward
        #     response (response timer was running)
        #   - the segment CONTAINING first_response_at → only the portion
        #     before first_response_at counts
        #   - segments AFTER first_response_at  → MUST contribute zero
        #
        # We verify this last invariant only.
        post_response_violators = []
        response_passed_queue = None
        if first_resp:
            for s in segments:
                e_at = datetime.fromisoformat(s.entered_at) if s.entered_at else None
                x_at = (datetime.fromisoformat(s.exited_at)
                        if s.exited_at else datetime.now(timezone.utc).replace(tzinfo=None))
                if e_at and e_at <= first_resp <= x_at:
                    response_passed_queue = s.queue_name
                # Any segment that fully starts after first_resp with response_loss > 0
                if e_at and e_at > first_resp and s.response_loss_minutes > 0:
                    post_response_violators.append(s.queue_name)

        resp_segments_pre_response = [
            s for s in segments if s.response_loss_minutes > 0
        ]

        top_loss = max(segments, key=lambda s: s.resolution_loss_minutes, default=None)
        breach_queue = next((s.queue_name for s in segments if s.breach_inside_segment), None)
        # If no segment contains the deadline (closed before / open with future deadline),
        # the breach_queue is empty. That's a meaningful answer.

        # bounces: queues visited ≥2 times
        from collections import Counter
        seg_counts = Counter(s.queue_name for s in segments)
        bounces = [{"queue": q, "visits": n} for q, n in seg_counts.items() if n >= 2]

        return {
            "ticket": {
                "ticket_id": t["ticket_id"],
                "ticket_number": t["ticket_number"],
                "title": t["title"],
                "created_at": t["created_at"].isoformat() if t["created_at"] else None,
                "first_response_at": t["first_response_at"].isoformat() if t["first_response_at"] else None,
                "resolution_at": t["resolution_at"].isoformat() if t["resolution_at"] else None,
                "current_queue": t["current_queue"],
                "current_state": t["current_state"],
                "current_owner": t["current_owner"],
                "is_closed": t["is_closed"],
            },
            "targets": {
                "response_target_seconds": response_target_seconds,
                "resolution_target_seconds": resolution_target_seconds,
            },
            "segments": [asdict(s) for s in segments],
            "summary": {
                "total_minutes": total_minutes,
                "total_segments": len(segments),
                "response_passed_in_queue": response_passed_queue,
                "response_segments_pre_response": len(resp_segments_pre_response),
                "post_response_response_loss_violators": post_response_violators,
                "top_loss_queue": top_loss.queue_name if top_loss else None,
                "top_loss_minutes": top_loss.resolution_loss_minutes if top_loss else 0,
                "breach_queue": breach_queue,
                "bounces": bounces,
                "first_response_rule_check": (
                    "ok"
                    if not post_response_violators
                    else f"violation: {len(post_response_violators)} segments after "
                         f"first response still report response_loss > 0"
                ),
            },
        }
