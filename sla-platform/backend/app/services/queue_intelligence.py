"""Queue Intelligence Engine — OTRS-specific queue flow analysis.

Core engine for the OTRS SLA Operations Intelligence Platform.
Processes real queue transition data to identify:
- Queue flow degradation
- Breach location forensics
- Transfer storms and loops
- Queue overload and stagnation
- ServiceDesk downstream damage
"""
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, func, text
from sqlalchemy.orm import Session

from app.domain.models import QueuePeriod, SLAMetric, TicketEvent, TicketSnapshot

logger = logging.getLogger(__name__)


class QueueIntelligenceEngine:

    @staticmethod
    def get_queue_flow_map(db: Session, days: int = 30) -> dict:
        """Build queue flow map — who transfers to whom, with breach data."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get all queue transitions with time info
        rows = db.execute(text("""
            SELECT
                te.ticket_id,
                te.queue_name AS src_queue,
                LEAD(te.queue_name) OVER (
                    PARTITION BY te.ticket_id ORDER BY te.event_seq
                ) AS dst_queue,
                te.event_time AS src_time,
                LEAD(te.event_time) OVER (
                    PARTITION BY te.ticket_id ORDER BY te.event_seq
                ) AS dst_time,
                te.event_type
            FROM ticket_events te
            WHERE te.event_time >= :cutoff
              AND te.queue_name IS NOT NULL
            ORDER BY te.ticket_id, te.event_seq
        """), {"cutoff": cutoff})

        flows: dict[str, dict[str, Any]] = {}
        ticket_flow_count: dict[tuple, int] = Counter()
        flow_breaches: dict[tuple, int] = Counter()
        flow_delays: dict[tuple, list[float]] = defaultdict(list)

        # Track which queues are breached for each ticket
        ticket_breach_queues: dict[int, set] = defaultdict(set)
        breach_rows = db.execute(text("""
            SELECT DISTINCT sm.ticket_id, sm.queue_name
            FROM sla_metrics sm
            WHERE sm.is_breach = TRUE
              AND sm.created_at >= :cutoff
        """), {"cutoff": cutoff})
        for r in breach_rows:
            ticket_breach_queues[r[0]].add(r[1])

        for row in rows:
            src = row.src_queue
            dst = row.dst_queue
            if not src or not dst or src == dst:
                continue
            key = (src, dst)
            ticket_flow_count[key] += 1

            if row.src_time and row.dst_time:
                delay = (row.dst_time - row.src_time).total_seconds() / 60
                if delay > 0:
                    flow_delays[key].append(delay)

            # Check if destination queue has breach
            if dst in ticket_breach_queues.get(row.ticket_id, set()):
                flow_breaches[key] += 1

        # Build structured output
        for (src, dst), count in ticket_flow_count.most_common(200):
            delays = flow_delays.get((src, dst), [])
            breaches_n = flow_breaches.get((src, dst), 0)

            if src not in flows:
                flows[src] = {"queue": src, "outbound": [], "total_out": 0}
            if dst not in flows:
                flows[dst] = {"queue": dst, "inbound": [], "total_in": 0}

            avg_delay = sum(delays) / len(delays) if delays else 0
            breach_pct = round(breaches_n / count * 100, 1) if count > 0 else 0

            flow_entry = {
                "target": dst,
                "count": count,
                "breaches": breaches_n,
                "breach_pct": breach_pct,
                "avg_delay_min": round(avg_delay, 1),
                "is_degraded": breach_pct > 30 or avg_delay > 480,
            }
            flows[src].setdefault("outbound", []).append(flow_entry)
            flows[src]["total_out"] = flows[src].get("total_out", 0) + count

        return {
            "flows": flows,
            "total_transitions": sum(ticket_flow_count.values()),
            "degraded_flows": [
                {"from": src, "to": dst, "count": c, "breaches": flow_breaches.get((src, dst), 0),
                 "breach_pct": round(flow_breaches.get((src, dst), 0) / c * 100, 1) if c else 0}
                for (src, dst), c in ticket_flow_count.most_common()
                if flow_breaches.get((src, dst), 0) / max(c, 1) > 0.3
            ],
        }

    @staticmethod
    def get_queue_forensics(db: Session, days: int = 30) -> dict:
        """Deep queue forensic analysis — per-queue SLA death location."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Per-queue aggregate metrics
        rows = db.execute(text("""
            SELECT
                sm.queue_name,
                COUNT(DISTINCT sm.ticket_id) AS ticket_count,
                COUNT(*) FILTER (WHERE sm.is_breach = TRUE) AS breach_count,
                AVG(sm.resolution_time_min) FILTER (WHERE sm.resolution_time_min IS NOT NULL) AS avg_resolution,
                AVG(sm.response_time_min) FILTER (WHERE sm.response_time_min IS NOT NULL) AS avg_response,
                AVG(sm.total_pause_min) FILTER (WHERE sm.total_pause_min IS NOT NULL) AS avg_pause,
                AVG(sm.active_work_min) FILTER (WHERE sm.active_work_min IS NOT NULL) AS avg_active,
                AVG(sm.waiting_time_min) FILTER (WHERE sm.waiting_time_min IS NOT NULL) AS avg_wait,
                COUNT(*) FILTER (WHERE sm.reassignments > 2) AS high_reassign,
                AVG(sm.reassignments) FILTER (WHERE sm.reassignments IS NOT NULL) AS avg_reassign
            FROM sla_metrics sm
            WHERE sm.created_at >= :cutoff
            GROUP BY sm.queue_name
            ORDER BY breach_count DESC
        """), {"cutoff": cutoff})

        queue_analysis = []
        for r in rows:
            total = r.ticket_count or 0
            breaches = r.breach_count or 0
            breach_pct = round(breaches / total * 100, 1) if total else 0
            avg_res = round(r.avg_resolution) if r.avg_resolution else 0
            avg_resp = round(r.avg_response) if r.avg_response else 0
            avg_pause = round(r.avg_pause) if r.avg_pause else 0
            avg_active = round(r.avg_active) if r.avg_active else 0
            avg_wait = round(r.avg_wait) if r.avg_wait else 0
            avg_reassign = round(r.avg_reassign, 1) if r.avg_reassign else 0
            high_reassign = r.high_reassign or 0

            # Overload score: weighted combination
            stagnation = avg_res / 480 if avg_res else 0  # >1 means over 8h
            breach_factor = breach_pct / 50  # >1 means >50% breaches
            reassign_factor = avg_reassign / 3  # >1 means >3 avg reassignments
            overload_score = round(
                stagnation * 0.4 + breach_factor * 0.4 + reassign_factor * 0.2, 2
            )

            needs_separate_sla = breach_pct > 50 or overload_score > 1.5
            is_systemically_degraded = overload_score > 1.0

            queue_analysis.append({
                "queue": r.queue_name,
                "total_tickets": total,
                "breaches": breaches,
                "breach_pct": breach_pct,
                "avg_resolution_min": avg_res,
                "avg_response_min": avg_resp,
                "avg_pause_min": avg_pause,
                "avg_active_work_min": avg_active,
                "avg_wait_min": avg_wait,
                "avg_reassignments": avg_reassign,
                "high_reassign_tickets": high_reassign,
                "overload_score": overload_score,
                "needs_separate_sla": needs_separate_sla,
                "systemically_degraded": is_systemically_degraded,
                "stagnation_label": "critical" if stagnation > 2 else "warning" if stagnation > 1 else "normal",
                "breach_severity": "critical" if breach_pct > 50 else "high" if breach_pct > 30 else "medium" if breach_pct > 10 else "low",
            })

        return {
            "queues": queue_analysis,
            "total_queues": len(queue_analysis),
            "queues_needing_sla_revision": [
                q for q in queue_analysis if q["needs_separate_sla"]
            ],
            "systemically_degraded": [
                q for q in queue_analysis if q["systemically_degraded"]
            ],
            "avg_breach_pct": round(
                sum(q["breach_pct"] for q in queue_analysis) / max(len(queue_analysis), 1), 1
            ),
        }

    @staticmethod
    def get_transfer_analytics(db: Session, days: int = 30) -> dict:
        """Analyze transfer storms, loops, and routing inefficiency."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Count transitions per ticket
        rows = db.execute(text("""
            SELECT
                te.ticket_id,
                COUNT(*) AS transition_count,
                COUNT(*) FILTER (
                    WHERE te.event_type LIKE '%Queue%'
                       OR te.queue_name IS DISTINCT FROM
                          LAG(te.queue_name) OVER (PARTITION BY te.ticket_id ORDER BY te.event_seq)
                ) AS queue_transitions
            FROM ticket_events te
            WHERE te.event_time >= :cutoff
            GROUP BY te.ticket_id
            ORDER BY queue_transitions DESC
            LIMIT 200
        """), {"cutoff": cutoff})

        high_transfer_tickets = []
        for r in rows:
            high_transfer_tickets.append({
                "ticket_id": r[0],
                "total_events": r[1],
                "queue_transitions": r[2],
            })

        # Detect bounce patterns (A->B->A)
        bounces = db.execute(text("""
            WITH ordered AS (
                SELECT
                    ticket_id,
                    queue_name,
                    event_seq,
                    LAG(queue_name, 2) OVER (PARTITION BY ticket_id ORDER BY event_seq) AS queue_before_prev
                FROM ticket_events
                WHERE event_time >= :cutoff AND queue_name IS NOT NULL
            )
            SELECT
                queue_before_prev AS queue,
                COUNT(*) AS bounce_count
            FROM ordered
            WHERE queue_name IS NOT NULL
              AND queue_before_prev IS NOT NULL
              AND queue_name = queue_before_prev
            GROUP BY queue_before_prev
            ORDER BY bounce_count DESC
            LIMIT 20
        """), {"cutoff": cutoff})

        bounce_queues = [{"queue": r[0], "bounces": r[1]} for r in bounces]

        # Transfer loops (tickets visiting same queue multiple times)
        loops = db.execute(text("""
            WITH queue_visits AS (
                SELECT
                    ticket_id,
                    queue_name,
                    COUNT(*) AS visits
                FROM ticket_events
                WHERE event_time >= :cutoff AND queue_name IS NOT NULL
                GROUP BY ticket_id, queue_name
                HAVING COUNT(*) > 2
            )
            SELECT
                queue_name,
                COUNT(DISTINCT ticket_id) AS tickets_in_loop,
                AVG(visits) AS avg_visits
            FROM queue_visits
            GROUP BY queue_name
            ORDER BY tickets_in_loop DESC
            LIMIT 20
        """), {"cutoff": cutoff})

        transfer_loops = [
            {"queue": r[0], "tickets_in_loop": r[1], "avg_visits": round(r[2], 1)}
            for r in loops
        ]

        return {
            "high_transfer_tickets": high_transfer_tickets,
            "bounce_queues": bounce_queues,
            "transfer_loops": transfer_loops,
            "total_tickets_with_transfers": len(high_transfer_tickets),
            "storm_threshold": 5,
            "warning": "Tickets with >5 queue transitions are in transfer storm territory",
        }

    @staticmethod
    def get_servicedesk_intelligence(db: Session, days: int = 30) -> dict:
        """ServiceDesk-specific analytics — intake, transfer quality, downstream damage."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Outbound from ServiceDesk
        sd_flows = db.execute(text("""
            WITH sd_out AS (
                SELECT
                    te.ticket_id,
                    te.queue_name AS src,
                    LEAD(te.queue_name) OVER (
                        PARTITION BY te.ticket_id ORDER BY te.event_seq
                    ) AS dst,
                    te.event_time,
                    LEAD(te.event_time) OVER (
                        PARTITION BY te.ticket_id ORDER BY te.event_seq
                    ) AS dst_time
                FROM ticket_events te
                WHERE te.event_time >= :cutoff
                  AND te.queue_name LIKE '%ServiceDesk%'
            )
            SELECT
                dst,
                COUNT(*) AS ticket_count,
                COUNT(*) FILTER (WHERE dst_time IS NOT NULL
                    AND (EXTRACT(EPOCH FROM (dst_time - event_time)) / 60) > 120) AS slow_transfers,
                AVG(EXTRACT(EPOCH FROM (dst_time - event_time)) / 60)
                    FILTER (WHERE dst_time IS NOT NULL) AS avg_transfer_min
            FROM sd_out
            WHERE dst IS NOT NULL
            GROUP BY dst
            ORDER BY ticket_count DESC
            LIMIT 30
        """), {"cutoff": cutoff})

        downstream = []
        for r in sd_flows:
            downstream.append({
                "target_queue": r[0],
                "tickets_received": r[1],
                "slow_transfers": r[2],
                "avg_transfer_delay_min": round(r[3], 1) if r[3] else 0,
                "transfer_quality": "poor" if (r[2] or 0) / max(r[1], 1) > 0.3 else "good",
            })

        # ServiceDesk intake load over time
        intake = db.execute(text("""
            SELECT
                DATE(te.event_time) AS day,
                COUNT(DISTINCT te.ticket_id) AS intake
            FROM ticket_events te
            WHERE te.event_time >= :cutoff
              AND te.queue_name LIKE '%ServiceDesk%'
              AND te.event_type = 'Create'
            GROUP BY DATE(te.event_time)
            ORDER BY day
        """), {"cutoff": cutoff})

        intake_trend = [{"date": str(r[0]), "intake": r[1]} for r in intake]

        return {
            "downstream": downstream,
            "intake_trend": intake_trend,
            "total_downstream_queues": len(downstream),
            "total_sd_intake": sum(d["tickets_received"] for d in downstream),
        }

    @staticmethod
    def get_ticket_lifecycle_forensic(db: Session, ticket_id: int) -> dict:
        """Full forensic timeline for a single ticket — queue-by-queue SLA analysis."""
        events = db.execute(text("""
            SELECT
                event_seq, event_time, event_type, queue_name, state_name, event_owner_name
            FROM ticket_events
            WHERE ticket_id = :tid
            ORDER BY event_seq
        """), {"tid": ticket_id}).all()

        if not events:
            return {"ticket_id": ticket_id, "error": "not found"}

        timeline = []
        queue_entries: dict[str, dict] = {}
        current_queue = None
        queue_entry_time = None
        queue_entry_owner = None

        for ev in events:
            entry = {
                "seq": ev.event_seq,
                "time": ev.event_time.isoformat() if ev.event_time else None,
                "type": ev.event_type,
                "queue": ev.queue_name,
                "state": ev.state_name,
                "owner": ev.event_owner_name,
            }
            timeline.append(entry)

            q = ev.queue_name
            if q and q != current_queue:
                if current_queue and queue_entry_time:
                    duration = (ev.event_time - queue_entry_time).total_seconds() / 60
                    if current_queue not in queue_entries:
                        queue_entries[current_queue] = {
                            "queue": current_queue,
                            "entries": [],
                            "total_duration_min": 0,
                            "owners": set(),
                        }
                    queue_entries[current_queue]["entries"].append({
                        "from": queue_entry_time.isoformat(),
                        "to": ev.event_time.isoformat(),
                        "duration_min": round(duration, 1),
                        "owner": queue_entry_owner,
                    })
                    queue_entries[current_queue]["total_duration_min"] += duration
                    if queue_entry_owner:
                        queue_entries[current_queue]["owners"].add(queue_entry_owner)

                current_queue = q
                queue_entry_time = ev.event_time
                queue_entry_owner = ev.event_owner_name

        # Final queue
        if current_queue and queue_entry_time and events:
            last_time = events[-1].event_time
            duration = (last_time - queue_entry_time).total_seconds() / 60
            if current_queue not in queue_entries:
                queue_entries[current_queue] = {
                    "queue": current_queue, "entries": [], "total_duration_min": 0, "owners": set()
                }
            queue_entries[current_queue]["entries"].append({
                "from": queue_entry_time.isoformat(),
                "to": last_time.isoformat(),
                "duration_min": round(duration, 1),
                "owner": queue_entry_owner,
            })
            queue_entries[current_queue]["total_duration_min"] += duration
            if queue_entry_owner:
                queue_entries[current_queue]["owners"].add(queue_entry_owner)

        # Check SLA metrics for this ticket
        sla_metrics = db.execute(text("""
            SELECT queue_name, is_breach, resolution_time_min, response_time_min
            FROM sla_metrics
            WHERE ticket_id = :tid
        """), {"tid": ticket_id}).all()

        breach_info = {}
        for sm in sla_metrics:
            breach_info[sm.queue_name] = {
                "is_breach": sm.is_breach,
                "resolution_min": sm.resolution_time_min,
                "response_min": sm.response_time_min,
            }

        # Enhance queue entries with SLA data
        for qname, qdata in queue_entries.items():
            sla = breach_info.get(qname, {})
            qdata["sla_breached"] = sla.get("is_breach", False)
            qdata["sla_resolution_min"] = sla.get("resolution_min")
            qdata["owners"] = list(qdata["owners"])

            # Determine where SLA died
            if sla.get("is_breach"):
                qdata["status"] = "BREACHED"
            elif qdata["total_duration_min"] > 240:
                qdata["status"] = "WARNING"
            else:
                qdata["status"] = "OK"

        # Find the exact breach location
        breached_queues = [
            {"queue": q, "duration_min": d["total_duration_min"],
             "owner": d["owners"][0] if d["owners"] else None}
            for q, d in queue_entries.items() if d.get("sla_breached")
        ]

        return {
            "ticket_id": ticket_id,
            "total_events": len(events),
            "total_queues": len(queue_entries),
            "queue_breakdown": sorted(
                [
                    {
                        "queue": q,
                        "total_duration_min": round(d["total_duration_min"]),
                        "entries": len(d["entries"]),
                        "owners": d["owners"],
                        "sla_breached": d.get("sla_breached", False),
                        "status": d.get("status", "OK"),
                    }
                    for q, d in queue_entries.items()
                ],
                key=lambda x: x["total_duration_min"],
                reverse=True,
            ),
            "breach_location": breached_queues,
            "timeline": timeline,
            "event_count": len(events),
        }

    @staticmethod
    def generate_root_cause(db: Session, ticket_id: int) -> str:
        """AI-style root cause explanation in Russian."""
        forensic = QueueIntelligenceEngine.get_ticket_lifecycle_forensic(db, ticket_id)
        if "error" in forensic:
            return "Тикет не найден"

        queue_breakdown = forensic.get("queue_breakdown", [])
        breach_location = forensic.get("breach_location", [])

        if not breach_location:
            return "SLA не было нарушено"

        parts = []
        total_time = sum(q["total_duration_min"] for q in queue_breakdown)

        # Primary breach queue
        primary = breach_location[0]
        primary_time_pct = round(primary["duration_min"] / max(total_time, 1) * 100, 1)
        parts.append(
            f"Тикет #{ticket_id}: {primary_time_pct}% времени ({primary['duration_min']} мин) "
            f"потеряно в очереди {primary['queue']}"
        )

        # Owner info
        if primary.get("owner"):
            parts.append(f"Ответственный в момент пробития: {primary['owner']}")

        # Check for bounces
        queues_visited = [q["queue"] for q in queue_breakdown]
        bounce_count = sum(
            1 for i in range(2, len(queues_visited))
            if queues_visited[i] == queues_visited[i - 2]
        )
        if bounce_count > 0:
            parts.append(f"Тикет отскочил между очередями {bounce_count} раз(а)")

        # Reassignments
        owners = set()
        for q in queue_breakdown:
            for o in q.get("owners", []):
                owners.add(o)
        if len(owners) > 2:
            parts.append(f"Тикет переназначался между {len(owners)} владельцами")

        # Time analysis
        long_queues = [
            q for q in queue_breakdown
            if q["total_duration_min"] > 240 and not q.get("sla_breached")
        ]
        if long_queues:
            worst = max(long_queues, key=lambda x: x["total_duration_min"])
            parts.append(
                f"Значительная задержка ({worst['total_duration_min']} мин) в очереди "
                f"{worst['queue']} (без пробития SLA, но с высокой задержкой)"
            )

        # Total time
        total_hours = round(total_time / 60, 1)
        parts.append(f"Общее время жизни тикета: {total_hours} ч")

        return "\n".join(parts)
